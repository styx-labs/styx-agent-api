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
    ParaformEvaluationState,
    ParaformEvaluationInputState,
    ParaformEvaluationOutputState,
    Queries,
    Job,
    CandidateInfo,
    SearchState,
)
from services.firestore import get_most_similar_jobs
from services.tavily import tavily_search_async
from services.azure_openai import llm


def generate_queries(state: ParaformEvaluationState):
    candidate = CandidateInfo(
        full_name=state["candidate_full_name"],
        context=state["candidate_context"],
        summary="",
    )

    structured_llm = llm.with_structured_output(Queries)
    system_instructions_query = report_planner_query_writer_instructions.format(
        candidate_full_name=candidate.full_name,
        candidate_context=candidate.context,
        number_of_queries=5,
    )
    results = structured_llm.invoke(
        [SystemMessage(content=system_instructions_query)]
        + [HumanMessage(content="Generate search queries.")]
    )

    search_state = SearchState(
        search_queries=results.queries, citations_str="", source_str="", citations=[]
    )

    return {"candidate": candidate, "search": search_state}


async def gather_sources(state: ParaformEvaluationState):
    search_docs = await tavily_search_async(state["search"].search_queries)
    source_str, citations = await deduplicate_and_format_sources(
        search_docs,
        max_tokens_per_source=10000,
        candidate_full_name=state["candidate"].full_name,
        candidate_context=state["candidate"].context,
    )

    state["search"].source_str = source_str
    state["search"].citations_str = "\n".join(
        [
            f"[{c['index']}]: {c['url']} (Confidence: {c['confidence']})"
            for c in citations
        ]
    )
    state["search"].citations = citations

    return {"search": state["search"]}


def write_candidate_summary(state: ParaformEvaluationState):
    summary_writer_instructions = """
You are an expert at evaluating candidates for jobs.
Write a concise summary of the candidate based on the provided sources.
Focus on their technical skills, experience, and achievements.
Keep it under 200 words and focus on factual information.

Here is the candidate's name:
{candidate_full_name}

Here is the candidate's basic profile:
{candidate_context}

Here are the sources about the candidate, ranked by confidence:
{source_str}

Use the confidence scores to prioritize the information from the sources.
    """
    content = llm.invoke(
        [
            SystemMessage(
                content=summary_writer_instructions.format(
                    candidate_full_name=state["candidate"].full_name,
                    candidate_context=state["candidate"].context,
                    source_str=state["search"].source_str,
                )
            )
        ]
        + [
            HumanMessage(
                content="Write a summary of the candidate based on the provided information. This will be used to find the most relevant roles for the candidate."
            )
        ]
    )

    state["candidate"].summary = content.content

    return {"candidate": state["candidate"]}


def get_relevant_jobs(state: ParaformEvaluationState):
    """Gets top similar jobs and extracts relevant fields"""
    jobs = get_most_similar_jobs(state["candidate"].summary, state["number_of_roles"])

    # Define default values for each field type
    list_fields = {
        "avoid_traits",
        "benefits",
        "company_locations",
        "requirements",
        "responsibilities",
        "role_locations",
        "tech_stack",
    }

    fields = [
        "avoid_traits",
        "benefits",
        "company_about",
        "company_description",
        "company_locations",
        "company_name",
        "equity",
        "experience_info",
        "ideal_candidate",
        "name",
        "paraform_link",
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
        "relevant_jobs": [
            Job(
                **{
                    field: job.get(field, [] if field in list_fields else "")
                    or ([] if field in list_fields else "")
                    for field in fields
                }
            )
            for job in jobs
        ]
    }


def initiate_job_evaluations(state: ParaformEvaluationState):
    """Initiates parallel evaluation for each job"""
    return [
        Send(
            f"evaluate_job_{i}",
            {
                "job_index": i,
                "current_job": job,
                **state,
            },
        )
        for i, job in enumerate(state["relevant_jobs"])
    ]


def compile_final_evaluation(state: ParaformEvaluationState):
    """Compiles all job evaluations into final report"""
    state["evaluations"].sort(key=lambda x: x.recommendation.score, reverse=True)
    return {
        "candidate_summary": state["candidate"].summary,
        "citations": state["search"].citations_str,
        "citations_detail": state["search"].citations,
    }


async def run_search(
    candidate_context: str,
    candidate_full_name: str,
    number_of_roles: int,
):
    builder = StateGraph(
        ParaformEvaluationState,
        input=ParaformEvaluationInputState,
        output=ParaformEvaluationOutputState,
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
    for i in range(number_of_roles):
        builder.add_node(f"evaluate_job_{i}", create_job_evaluation_subgraph(i))

    builder.add_conditional_edges(
        "get_relevant_jobs",
        initiate_job_evaluations,
        [f"evaluate_job_{i}" for i in range(number_of_roles)],
    )

    # Reduces the subgraphs into a single evaluation
    for i in range(number_of_roles):
        builder.add_edge(f"evaluate_job_{i}", "compile_final_evaluation")

    builder.add_edge("compile_final_evaluation", END)

    graph = builder.compile()

    return await graph.ainvoke(
        ParaformEvaluationInputState(
            candidate_full_name=candidate_full_name,
            candidate_context=candidate_context,
            number_of_roles=number_of_roles,
        )
    )
