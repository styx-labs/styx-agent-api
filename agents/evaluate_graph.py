from langgraph.constants import Send
from langgraph.graph import START, END, StateGraph
from services.helper_functions import (
    deduplicate_and_format_sources,
    heuristic_validator,
    llm_validator,
    distill_source,
    get_recommendation,
    get_trait_evaluation,
    get_search_queries,
)
from agents.types import (
    EvaluationState,
    EvaluationInputState,
    EvaluationOutputState,
    SearchQuery
)
from services.tavily import tavily_search_async
from services.exa import exa_search_async


def generate_queries(state: EvaluationState):
    job_description = state["job_description"]
    candidate_context = state["candidate_context"]
    number_of_queries = state["number_of_queries"]
    candidate_full_name = state["candidate_full_name"]

    content = get_search_queries(candidate_full_name, candidate_context, job_description, number_of_queries)

    # Add a query for the candidate's name
    content.queries.append(SearchQuery(search_query=candidate_full_name))
    return {"search_queries": content.queries}


async def gather_sources(state: EvaluationState):
    search_docs = await tavily_search_async(state["search_queries"])
    sources_dict = deduplicate_and_format_sources(search_docs)
    return {"sources_dict": sources_dict}


def validate_and_distill_source(state: EvaluationState):
    source = state["sources_dict"][state["source"]]
    candidate_full_name = state["candidate_full_name"]
    candidate_context = state["candidate_context"]
    confidence_threshold = state["confidence_threshold"]

    if not heuristic_validator(source["raw_content"] if source["raw_content"] else "", source["title"], candidate_full_name):
        return {"validated_sources": []}

    llm_output = llm_validator(
        source["raw_content"], candidate_full_name, candidate_context
    )
    if llm_output.confidence < confidence_threshold:
        return {"validated_sources": []}

    source["weight"] = llm_output.confidence
    source["distilled_content"] = distill_source(
        source["raw_content"], candidate_full_name
    ).distilled_source
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
            {"index": i, "url": source["url"], "confidence": source["weight"], "distilled_content": source["distilled_content"]}
        )

    return {"source_str": formatted_text.strip(), "citations": citation_list}


def initiate_source_validation(state: EvaluationState):
    return [
        Send("validate_and_distill_source", {"source": source, **state})
        for source in state["sources_dict"].keys()
    ]


def evaluate_trait(state: EvaluationState):
    section = state["section"]
    section_description = state["section_description"]
    source_str = state["source_str"]
    candidate_full_name = state["candidate_full_name"]
    candidate_context = state["candidate_context"]

    content = get_trait_evaluation(section, section_description, candidate_full_name, candidate_context, source_str)
    
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
    
    content = get_recommendation(job_description, candidate_full_name, completed_sections_str).recommendation

    return {
        "summary": content,
        "overall_score": overall_score
    }


def compile_evaluation(state: EvaluationState):
    key_traits = state["key_traits"]
    completed_sections = state["completed_sections"]
    citations = state["citations"]
    ordered_sections = []
    for trait in key_traits:
        for section in completed_sections:
            if section["section"] == trait["trait"]:
                ordered_sections.append(section)

    return {"sections": ordered_sections, "citations": citations}


def initiate_evaluation(state: EvaluationState):
    return [
        Send("evaluate_trait", {"section": t["trait"], "section_description": t["description"], **state}) for t in state["key_traits"]
    ]


async def run_search(
    job_description: str,
    candidate_context: str,
    candidate_full_name: str,
    key_traits: list[dict],
    number_of_queries: int,
    confidence_threshold: float,
) -> EvaluationOutputState:
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
            number_of_queries=number_of_queries,
            confidence_threshold=confidence_threshold,
        )
    )
