# Third party imports
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send
from langgraph.graph import START, END, StateGraph

# Local imports
from agents.job_subgraph import create_job_evaluation_subgraph
from agents.search_helper import (
    deduplicate_and_format_sources,
    report_planner_query_writer_instructions,
)
from agents.types import (
    EvaluationState,
    EvaluationInputState,
    EvaluationOutputState,
    Queries,
)
from services.firestore import get_most_similar_jobs
from services.tavily import tavily_search_async
from services.azure_openai import llm

NUMBER_OF_RELEVANT_JOBS = 5


def generate_queries(state: EvaluationState):
    candidate_context = state["candidate_context"]
    number_of_queries = state["number_of_queries"]
    candidate_full_name = state["candidate_full_name"]

    structured_llm = llm.with_structured_output(Queries)
    system_instructions_query = report_planner_query_writer_instructions.format(
        candidate_full_name=candidate_full_name,
        candidate_context=candidate_context,
        number_of_queries=number_of_queries,
    )
    results = structured_llm.invoke(
        [SystemMessage(content=system_instructions_query)]
        + [HumanMessage(content="Generate search queries.")]
    )
    return {"search_queries": results.queries}


async def gather_sources(state: EvaluationState):
    candidate_context = state["candidate_context"]
    candidate_full_name = state["candidate_full_name"]
    search_queries = state["search_queries"]

    search_docs = await tavily_search_async(search_queries)
    source_str, citation_str = await deduplicate_and_format_sources(
        search_docs,
        max_tokens_per_source=10000,
        candidate_full_name=candidate_full_name,
        candidate_context=candidate_context,
    )

    return {"source_str": source_str, "citations": citation_str}


def write_candidate_summary(state: EvaluationState):
    summary_writer_instructions = """
    You are an expert at evaluating candidates for jobs.
    Write a concise summary of the candidate based on the provided sources.
    Focus on their technical skills, experience, and achievements.
    Keep it under 200 words and focus on factual information.

    Here is the candidate's name:
    {candidate_full_name}
    
    Here is the candidate's basic profile:
    {candidate_context}
    
    Here are the sources about the candidate:
    {source_str}
    """

    source_str = state["source_str"]
    candidate_full_name = state["candidate_full_name"]
    candidate_context = state["candidate_context"]

    content = llm.invoke(
        [
            SystemMessage(
                content=summary_writer_instructions.format(
                    candidate_full_name=candidate_full_name,
                    candidate_context=candidate_context,
                    source_str=source_str,
                )
            )
        ]
        + [
            HumanMessage(
                content="Write a summary of the candidate based on the provided information. This will be used to find the most relevant roles for the candidate."
            )
        ]
    )

    return {"candidate_summary": content.content}


def get_relevant_jobs(state: EvaluationState):
    """Gets top 10 similar jobs and extracts relevant fields"""
    jobs = get_most_similar_jobs(state["candidate_summary"], NUMBER_OF_RELEVANT_JOBS)

    fields = [
        "avoid_traits",
        "company_description",
        "company_about",
        "company_name",
        "experience_info",
        "ideal_candidate",
        "name",
        "recruiting_advice",
        "requirements",
        "responsibilities",
        "role_description",
        "role_locations",
        "salary_lower_bound",
        "salary_upper_bound",
        "tech_stack",
        "visa_text",
        "visa_text_more",
        "workplace",
        "years_experience_max",
        "years_experience_min",
    ]

    return {
        "relevant_jobs": [{field: job.get(field) for field in fields} for job in jobs]
    }


def initiate_job_evaluations(state: EvaluationState):
    """Initiates parallel evaluation for each job"""
    tasks = []
    for i, job in enumerate(state["relevant_jobs"]):
        # Helper function to handle both string and list values
        def format_field(field):
            if isinstance(field, list):
                return "\n".join(field)
            return str(field) if field is not None else ""

        # Format each field
        current_job = "\n\n".join(
            [
                format_field(job.get("role_description")),
                format_field(job.get("responsibilities")),
                format_field(job.get("requirements")),
                format_field(job.get("ideal_candidate")),
                format_field(job.get("recruiting_advice")),
                format_field(job.get("company_description")),
                format_field(job.get("experience_info")),
                format_field(job.get("company_name")),
                format_field(job.get("company_about")),
            ]
        )

        tasks.append(
            Send(
                f"evaluate_job_{i}",
                {
                    "job_index": i,
                    "current_job": current_job,
                    "sections": job["requirements"],
                    "company_name": job.get("company_name", "Unknown Company"),
                    "role": job.get("name", "Unknown Role"),
                    **state,
                },
            )
        )
    return tasks


def compile_final_evaluation(state: EvaluationState):
    """Compiles all job evaluations into final report"""

    # Create structured JSON output
    final_evaluation = {
        "candidate_summary": state["candidate_summary"],
        "job_evaluations": state["evaluations"],
        "citations": state["citations"],
    }

    return {"final_evaluation": final_evaluation}


async def run_search(
    candidate_context: str,
    candidate_full_name: str,
    number_of_queries: int,
):
    builder = StateGraph(
        EvaluationState, input=EvaluationInputState, output=EvaluationOutputState
    )

    # Main nodes
    builder.add_node("generate_queries", generate_queries)
    builder.add_node("gather_sources", gather_sources)
    builder.add_node("write_candidate_summary", write_candidate_summary)
    builder.add_node("get_relevant_jobs", get_relevant_jobs)
    builder.add_node("compile_final_evaluation", compile_final_evaluation)

    # Main edges
    builder.add_edge(START, "generate_queries")
    builder.add_edge("generate_queries", "gather_sources")
    builder.add_edge("gather_sources", "write_candidate_summary")
    builder.add_edge("write_candidate_summary", "get_relevant_jobs")

    # Creates subgraphs for each job
    for i in range(NUMBER_OF_RELEVANT_JOBS):
        builder.add_node(f"evaluate_job_{i}", create_job_evaluation_subgraph(i))

    builder.add_conditional_edges(
        "get_relevant_jobs",
        initiate_job_evaluations,
        [f"evaluate_job_{i}" for i in range(NUMBER_OF_RELEVANT_JOBS)],
    )

    # Reduces the subgraphs into a single evaluation
    for i in range(NUMBER_OF_RELEVANT_JOBS):
        builder.add_edge(f"evaluate_job_{i}", "compile_final_evaluation")

    builder.add_edge("compile_final_evaluation", END)

    graph = builder.compile()

    return await graph.ainvoke(
        EvaluationInputState(
            candidate_full_name=candidate_full_name,
            candidate_context=candidate_context,
            number_of_queries=number_of_queries,
        )
    )
