# Third party imports
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send
from langgraph.graph import START, END, StateGraph
from pydantic import BaseModel

# Local imports
from agents.search_helper import (
    deduplicate_and_format_sources,
    report_planner_query_writer_instructions,
    heuristic_validator,
    llm_validator,
    distill_source,
)
from agents.types import (
    EvaluationState,
    EvaluationInputState,
    EvaluationOutputState,
    Queries,
    SearchQuery,
)
from agents.get_key_traits import get_key_traits
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

    # Add a query for the candidate's name
    results.queries.append(SearchQuery(search_query=candidate_full_name))
    return {"search_queries": results.queries}


async def gather_sources(state: dict) -> dict:
    search_docs = await tavily_search_async(state["search_queries"])
    sources_dict = deduplicate_and_format_sources(search_docs)
    return {"sources_dict": sources_dict}


def validate_and_distill_source(state: EvaluationState):
    source = state["sources_dict"][state["source"]]
    candidate_full_name = state["candidate_full_name"]
    candidate_context = state["candidate_context"]

    initial_content = source.get("content", "") + " " + source.get("title", "")
    if not heuristic_validator(initial_content, source["title"], candidate_full_name):
        return {"validated_sources": []}

    llm_output = llm_validator(
        source["raw_content"], candidate_full_name, candidate_context
    )
    if llm_output.confidence <= 0.5:
        return {"validated_sources": []}

    source["weight"] = llm_output.confidence
    source["distilled_content"] = distill_source(
        source["raw_content"], candidate_full_name
    )
    return {"validated_sources": [source]}


def compile_sources(state: EvaluationState):
    validated_sources = state["validated_sources"]
    ranked_sources = sorted(validated_sources, key=lambda x: x["weight"], reverse=True)

    formatted_text = "Sources:\n\n"
    citation_list = []

    for i, source in enumerate(ranked_sources, 1):
        formatted_text += (
            f"[{i}]: {source['title']}:\n"
            f"URL: {source['url']}\n"
            f"Relevant content from source: {source['distilled_content']} "
            f"(Confidence: {source['weight']})\n===\n"
        )

        citation_list.append(
            {"index": i, "url": source["url"], "confidence": source["weight"]}
        )

    return {"source_str": formatted_text.strip(), "citations": citation_list}


def initiate_source_validation(state: EvaluationState):
    return [
        Send("validate_and_distill_source", {"source": source, **state})
        for source in state["sources_dict"].keys()
    ]


def evaluate_trait(state: EvaluationState):
    class EvaluationOutput(BaseModel):
        score: int
        evaluation: str

    evaluation_instructions = """
    You are an expert at evaluating candidates for a job.
    You are given a specific trait that you are evaluating the candidate on.
    You are also given a string of sources that contain information about the candidate.
    Write a evaluation of the candidate in this specific trait based on the provided information.
    It is possible that there is no information about the candidate in this trait - if this is the case, please mention that no information was found regarding the trait, not that the candidate does not have the trait.

    Output two values:
    - An integer score from 0 to 10 that rates the candidate based on their experience in this trait.
    - A string of text that is the evaluation of the candidate in this specific trait based on the provided information. This should be a single sentence that is less than 50 words.

    Here is the trait you are evaluating the candidate on:
    {section}
    Here is the candidate's name:
    {candidate_full_name}
    Here is the candidate's basic profile:
    {candidate_context}
    Here are the sources about the candidate:
    {source_str}

    When you mention information that you get from a source, please include a citation in your evaluation by citing the number of the source that links to the url in a clickable markdown format.
    For example, if you use information from sources 3 and 7, cite them like this: [3](url), [7](url). 
    Don't include a citation if you are not referencing a source.
    """

    structured_llm = llm.with_structured_output(EvaluationOutput)

    section = state["section"]
    source_str = state["source_str"]
    candidate_full_name = state["candidate_full_name"]
    candidate_context = state["candidate_context"]
    content = structured_llm.invoke(
        [
            SystemMessage(
                content=evaluation_instructions.format(
                    section=section,
                    candidate_full_name=candidate_full_name,
                    candidate_context=candidate_context,
                    source_str=source_str,
                )
            )
        ]
        + [
            HumanMessage(
                content="Score and evaluate the candidate in this specific trait based on the provided information."
            )
        ]
    )
    return {
        "completed_sections": [
            {"section": section, "content": content.evaluation, "score": content.score}
        ]
    }


def write_recommendation(state: EvaluationState):
    candidate_full_name = state["candidate_full_name"]
    completed_sections = state["completed_sections"]
    job_description = state["job_description"]
    completed_sections_str = "\n\n".join([s["content"] for s in completed_sections])
    overall_score = sum([s["score"] for s in completed_sections]) / len(
        completed_sections
    )
    recommmendation_instructions = """
    You are an expert at evaluating candidates for a job.
    You are given a specific job description and a report evaluating specific areas of the candidate.
    Write a recommendation on how good of a fit the candidate is for the job that is based on the information provided.
    This should be a short 2-3 sentence evaluation on how well the candidate fits the job description based on the information provided.
    Here is the job description:
    {job_description}
    Here is the candidate's name:
    {candidate_full_name}
    Here is the report about the candidate:
    {completed_sections}

    When you mention information that you get from a source, please include a citation in your evaluation by citing the number of the source that links to the url in a clickable markdown format.
    For example, if you use information from sources 3 and 7, cite them like this: [3](url), [7](url). 
    Don't include a citation if you are not referencing a source.
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
            {
                "section": "recommendation",
                "content": content.content,
                "score": overall_score,
            }
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
    return {"sections": ordered_sections, "citations": citations}


def initiate_evaluation(state: EvaluationState):
    return [
        Send("evaluate_trait", {"section": t, **state}) for t in state["key_traits"]
    ]


async def run_search_no_paraform(
    job_description: str,
    candidate_context: str,
    candidate_full_name: str,
) -> EvaluationOutputState:
    NUMBER_OF_QUERIES = 5

    key_traits = get_key_traits(job_description)["key_traits"] or [
        "Technical Skills",
        "Experience",
        "Education",
        "Entrepreneurship",
    ]

    builder = StateGraph(
        EvaluationState, input=EvaluationInputState, output=EvaluationOutputState
    )
    builder.add_node("generate_queries", generate_queries)
    builder.add_node("gather_sources", gather_sources)
    builder.add_node("validate_and_distill_source", validate_and_distill_source)
    builder.add_node("compile_sources", compile_sources)
    builder.add_node("evaluate_trait", evaluate_trait)
    builder.add_node("write_recommendation", write_recommendation)
    builder.add_node("compile_evaluation", compile_evaluation)

    builder.add_edge(START, "generate_queries")
    builder.add_edge("generate_queries", "gather_sources")
    builder.add_conditional_edges(
        "gather_sources", initiate_source_validation, ["validate_and_distill_source"]
    )
    builder.add_edge("validate_and_distill_source", "compile_sources")
    builder.add_conditional_edges(
        "compile_sources", initiate_evaluation, ["evaluate_trait"]
    )
    builder.add_edge("evaluate_trait", "write_recommendation")
    builder.add_edge("write_recommendation", "compile_evaluation")
    builder.add_edge("compile_evaluation", END)

    graph = builder.compile()

    return await graph.ainvoke(
        EvaluationInputState(
            job_description=job_description,
            candidate_context=candidate_context,
            candidate_full_name=candidate_full_name,
            key_traits=key_traits,
            number_of_queries=NUMBER_OF_QUERIES,
        )
    )
