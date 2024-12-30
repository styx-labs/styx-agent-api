# Third party imports
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send
from langgraph.graph import START, END, StateGraph

# Local imports
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

from services.azure_openai import llm
from services.tavily import tavily_search_async


def generate_queries(state: EvaluationState):
    job_description = state["job_description"]
    candidate_context = state["candidate_context"]
    number_of_queries = state["number_of_queries"]
    candidate_full_name = state["candidate_full_name"]
    structured_llm = llm.with_structured_output(Queries)
    system_instructions_query = report_planner_query_writer_instructions.format(
        job_description=job_description,
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


def write_section(state: EvaluationState):
    section_writer_instructions = """
    You are an expert at evaluating candidates for a job.
    You are given a specific trait that you are evaluating the candidate on.
    You are also given a string of sources that contain information about the candidate.
    Write a evaluation of the candidate in this specific trait based on the provided information.
    It is possible that the candidate does not have any experience that matches the trait - if this is the case, please note this in your evaluation.
    
    Each source is cited by a number.
    When you mention information that you get from a source, please include a citation in your evaluation by citing the number of the source that links to the url in a clickable markdown format.
    For example, if you use information from sources 3 and 7, cite them like this: [[3]](url), [[7]](url). 
    Don't include a citation if you are not referencing a source.
    Guidlines for writing:
    - Strict 50-150 word limit
    - No marketing language
    - Technical focus
    - Write in simple, clear language
    - Start with your most important insight in **bold**
    - Use short paragraphs (2-3 sentences max)
    - Use Markdown format for headings, bold, etc. Use ### for the section heading, which should be "Evaluation of <trait>".
    Here is the trait you are evaluating the candidate on:
    {section}
    Here is the candidate's name:
    {candidate_full_name}
    Here is the candidate's basic profile:
    {candidate_context}
    Here are the sources about the candidate:
    {source_str}
    """
    section = state["section"]
    source_str = state["source_str"]
    candidate_full_name = state["candidate_full_name"]
    candidate_context = state["candidate_context"]
    content = llm.invoke(
        [
            SystemMessage(
                content=section_writer_instructions.format(
                    section=section,
                    candidate_full_name=candidate_full_name,
                    candidate_context=candidate_context,
                    source_str=source_str,
                )
            )
        ]
        + [
            HumanMessage(
                content="Write a evaluation of the candidate in this specific trait based on the provided information."
            )
        ]
    )
    return {"completed_sections": [{"section": section, "content": content.content}]}


def write_recommendation(state: EvaluationState):
    candidate_full_name = state["candidate_full_name"]
    completed_sections = state["completed_sections"]
    job_description = state["job_description"]
    completed_sections_str = "\n\n".join([s["content"] for s in completed_sections])
    recommmendation_instructions = """
    You are an expert at evaluating candidates for a job.
    You are given a specific job description and a report evaluating specific areas of the candidate.
    Write a recommendation on how good of a fit the candidate is for the job that is based on the information provided.
    This should be a short 2-3 sentence evaluation on how well the candidate fits the job description based on the information provided.
    Do not include any evidence from the sources in your evaluation.
    Please write the recommendation in Markdown format, starting the section with a heading: ## Overall Evaluation
    Here is the job description:
    {job_description}
    Here is the candidate's name:
    {candidate_full_name}
    Here is the report about the candidate:
    {completed_sections}
    """
    formatted_prompt = recommmendation_instructions.format(
        job_description=job_description,
        candidate_full_name=candidate_full_name,
        completed_sections=completed_sections_str,
    )
    content = llm.invoke(
        [SystemMessage(content=formatted_prompt)]
        + [
            HumanMessage(
                content="Write a recommendation on how good of a fit the candidate is for the job based on the provided information."
            )
        ]
    )
    return {
        "completed_sections": [
            {"section": "recommendation", "content": content.content}
        ]
    }


def compile_evaluation(state: EvaluationState):
    key_traits = ["recommendation"] + state["key_traits"]
    completed_sections = state["completed_sections"]
    citations = state["citations"]
    ordered_sections = []
    for trait in key_traits:
        for section in completed_sections:
            if section["section"] == trait:
                ordered_sections.append(section)
    ordered_sections.append({"section": "citations", "content": citations})
    all_sections = "\n\n".join([s["content"] for s in ordered_sections])
    return {"final_evaluation": all_sections}


def initiate_section_writing(state: EvaluationState):
    return [Send("write_section", {"section": t, **state}) for t in state["key_traits"]]


async def run_search_(
    job_description: str,
    candidate_context: str,
    candidate_full_name: str,
    key_traits: list[str],
    number_of_queries: int,
):
    builder = StateGraph(
        EvaluationState, input=EvaluationInputState, output=EvaluationOutputState
    )
    builder.add_node("generate_queries", generate_queries)
    builder.add_node("gather_sources", gather_sources)
    builder.add_node("write_section", write_section)
    builder.add_node("write_recommendation", write_recommendation)
    builder.add_node("compile_evaluation", compile_evaluation)
    builder.add_edge(START, "generate_queries")
    builder.add_edge("generate_queries", "gather_sources")
    builder.add_conditional_edges(
        "gather_sources", initiate_section_writing, ["write_section"]
    )
    builder.add_edge("write_section", "write_recommendation")
    builder.add_edge("write_recommendation", "compile_evaluation")
    builder.add_edge("compile_evaluation", END)
    graph = builder.compile()
    return await graph.ainvoke(
        EvaluationInputState(
            job_description=job_description,
            candidate_context=candidate_context,
            candidate_full_name=candidate_full_name,
            key_traits=key_traits,
            number_of_queries=number_of_queries,
        )
    )
