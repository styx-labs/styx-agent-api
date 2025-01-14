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
    SearchQuery,
    CachedEvaluationInputState,
)
from models import TraitType
from services.tavily import tavily_search_async
from services.exa import exa_search_async


def generate_queries(state: EvaluationState):
    job_description = state["job_description"]
    candidate_context = state["candidate_context"]
    number_of_queries = state["number_of_queries"]
    candidate_full_name = state["candidate_full_name"]

    content = get_search_queries(
        candidate_full_name, candidate_context, job_description, number_of_queries
    )

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

    if not heuristic_validator(
        source["raw_content"] if source["raw_content"] else "",
        source["title"],
        candidate_full_name,
    ):
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
            {
                "index": i,
                "url": source["url"],
                "confidence": source["weight"],
                "distilled_content": source["distilled_content"],
            }
        )

    return {"source_str": formatted_text.strip(), "citations": citation_list}


def initiate_source_validation(state: EvaluationState):
    return [
        Send("validate_and_distill_source", {"source": source, **state})
        for source in state["sources_dict"].keys()
    ]


def evaluate_trait(state: EvaluationState):
    trait = state["trait"]  # This should be the full KeyTrait object
    source_str = state["source_str"]
    candidate_full_name = state["candidate_full_name"]
    candidate_context = state["candidate_context"]

    content = get_trait_evaluation(
        trait.trait,  # Access as object attribute
        trait.description,  # Access as object attribute
        candidate_full_name,
        candidate_context,
        source_str,
        trait_type=trait.trait_type,
        value_type=trait.value_type,
    )

    # Convert the trait value to a normalized score for overall calculation
    normalized_score = 0

    # Convert value to appropriate type based on trait_type
    try:
        if content.trait_type == "TraitType.SCORE":
            # Ensure numeric value for score type
            value = (
                float(content.value)
                if isinstance(content.value, str)
                else content.value
            )
            normalized_score = value  # Already 0-10
        elif content.trait_type == "TraitType.BOOLEAN":
            # Handle both string and boolean representations
            if isinstance(content.value, str):
                value = content.value.lower() in ["true", "yes", "1"]
            else:
                value = bool(content.value)
            normalized_score = 10 if value else 0

    except Exception as e:
        print(f"Error normalizing score for trait {trait.trait}: {str(e)}")
        normalized_score = 0

    return {
        "completed_sections": [
            {
                "section": trait.trait,
                "content": content.evaluation,
                "value": content.value,
                "trait_type": content.trait_type,
                "value_type": trait.value_type,
                "normalized_score": normalized_score,
                "required": trait.required,
            }
        ]
    }


def write_recommendation(state: EvaluationState):
    candidate_full_name = state["candidate_full_name"]
    completed_sections = state["completed_sections"]
    job_description = state["job_description"]
    completed_sections_str = "\n\n".join([s["content"] for s in completed_sections])

    # Calculate overall score only from required traits
    required_sections = [
        s for s in completed_sections if s["required"] and "normalized_score" in s
    ]
    if required_sections:
        overall_score = sum([s["normalized_score"] for s in required_sections]) / len(
            required_sections
        )
    else:
        overall_score = 0

    content = get_recommendation(
        job_description, candidate_full_name, completed_sections_str
    ).recommendation

    return {"summary": content, "overall_score": overall_score}


def compile_evaluation(state: EvaluationState):
    key_traits = state["key_traits"]
    completed_sections = state["completed_sections"]
    citations = state["citations"]
    ordered_sections = []

    for trait in key_traits:
        for section in completed_sections:
            if section["section"] == trait.trait:
                ordered_section = {
                    "section": section["section"],
                    "content": section["content"],
                    "trait_type": section["trait_type"],
                    "value": section["value"],
                    "value_type": section["value_type"],
                    "normalized_score": section["normalized_score"],
                    "required": section["required"],
                }
                ordered_sections.append(ordered_section)

    return {"sections": ordered_sections, "citations": citations}


def initiate_evaluation(state: EvaluationState):
    return [
        Send(
            "evaluate_trait",
            {"trait": t, **state},  # Pass the entire KeyTrait object
        )
        for t in state["key_traits"]
    ]


def initiate_cached_evaluation(state: EvaluationState):
    return {}


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

async def run_search_cached(
    job_description: str,
    candidate_context: str,
    candidate_full_name: str,
    key_traits: list[dict],
    citations: list[dict],
    source_str: str,
) -> EvaluationOutputState:
    builder = StateGraph(
        EvaluationState, input=CachedEvaluationInputState, output=EvaluationOutputState
    )

    builder.add_node("evaluate_trait", evaluate_trait)
    builder.add_node("write_recommendation", write_recommendation)
    builder.add_node("compile_evaluation", compile_evaluation)
    builder.add_node("initiate_cached_evaluation", initiate_cached_evaluation)

    builder.add_edge(START, "initiate_cached_evaluation")
    builder.add_conditional_edges(
        "initiate_cached_evaluation", initiate_evaluation, ["evaluate_trait"]
    )
    builder.add_edge("evaluate_trait", "write_recommendation")
    builder.add_edge("write_recommendation", "compile_evaluation")
    builder.add_edge("compile_evaluation", END)

    graph = builder.compile()

    return await graph.ainvoke(
        CachedEvaluationInputState(
            job_description=job_description,
            candidate_context=candidate_context,
            candidate_full_name=candidate_full_name,
            key_traits=key_traits,
            citations=citations,
            source_str=source_str,
        )
    )
