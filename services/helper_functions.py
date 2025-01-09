import re
from langchain_core.messages import HumanMessage, SystemMessage
from services.azure_openai import llm
from langsmith import traceable
import httpx
import asyncio
from bs4 import BeautifulSoup
from agents.types import (
    KeyTraitsOutput,
    QueriesOutput,
    ValidationOutput,
    DistillSourceOutput,
    RecommendationOutput,
    TraitEvaluationOutput,
)
from agents.prompts import (
    key_traits_prompt,
    validation_prompt,
    distill_source_prompt,
    recommendation_prompt,
    trait_evaluation_prompt,
    search_query_prompt,
    reachout_message_prompt_linkedin,
    reachout_message_prompt_email,
)
from typing import List


def clean_text(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower())


def heuristic_validator(content, title, candidate_full_name: str) -> bool:
    cleaned_link_text = clean_text(content + " " + title)
    cleaned_candidate_full_name = clean_text(candidate_full_name)
    name_parts = cleaned_candidate_full_name.split()

    score = 0.0

    if cleaned_candidate_full_name in cleaned_link_text:
        score += 1.0

    name_part_matches = sum(
        1 for part in name_parts if f" {part} " in f" {cleaned_link_text} "
    )
    score += (name_part_matches / len(name_parts)) * 0.5

    return score >= 0.5


@traceable(name="get_search_queries")
def get_search_queries(
    candidate_full_name: str,
    candidate_context: str,
    job_description: str,
    number_of_queries: int,
) -> QueriesOutput:
    structured_llm = llm.with_structured_output(QueriesOutput)
    output = structured_llm.invoke(
        [
            SystemMessage(
                content=search_query_prompt.format(
                    candidate_full_name=candidate_full_name,
                    candidate_context=candidate_context,
                    job_description=job_description,
                    number_of_queries=number_of_queries,
                )
            )
        ]
        + [HumanMessage(content="Generate search queries.")]
    )
    return output


@traceable(name="llm_validator")
def llm_validator(
    raw_content, candidate_full_name: str, candidate_context: str
) -> ValidationOutput:
    structured_llm = llm.with_structured_output(ValidationOutput)
    output = structured_llm.invoke(
        [
            SystemMessage(
                content=validation_prompt.format(
                    candidate_full_name=candidate_full_name,
                    candidate_context=candidate_context,
                    raw_content=raw_content,
                )
            )
        ]
        + [
            HumanMessage(
                content="Validate if this webpage is about the candidate in question."
            )
        ]
    )
    return output


@traceable(name="distill_source")
def distill_source(raw_content, candidate_full_name: str) -> DistillSourceOutput:
    structured_llm = llm.with_structured_output(DistillSourceOutput)
    output = structured_llm.invoke(
        [
            SystemMessage(
                content=distill_source_prompt.format(
                    raw_content=raw_content, candidate_full_name=candidate_full_name
                )
            )
        ]
        + [
            HumanMessage(
                content="Extract the relevant information about the given person from the raw HTML."
            )
        ]
    )
    return output


def normalize_search_results(search_response) -> list:
    """Convert different search response formats into a unified list of results."""
    if isinstance(search_response, dict):
        return search_response["results"]
    elif isinstance(search_response, list):
        sources_list = []
        for response in search_response:
            if isinstance(response, dict) and "results" in response:
                sources_list.extend(response["results"])
            else:
                sources_list.extend(response)
        return sources_list
    raise ValueError(
        "Input must be either a dict with 'results' or a list of search results"
    )


def deduplicate_and_format_sources(search_response) -> dict:
    """Process search results and return formatted sources with citations."""
    # Get unified list of results
    sources_list = normalize_search_results(search_response)

    # Deduplicate by URL
    unique_sources = {source["url"]: source for source in sources_list}

    return unique_sources


@traceable(name="get_key_traits")
def get_key_traits(job_description: str) -> KeyTraitsOutput:
    structured_llm = llm.with_structured_output(KeyTraitsOutput)
    return structured_llm.invoke(
        [
            SystemMessage(
                content=key_traits_prompt.format(job_description=job_description)
            ),
            HumanMessage(
                content="Generate a list of key traits relevant to the job description."
            ),
        ]
    )


@traceable(name="get_recommendation")
def get_recommendation(
    job_description: str, candidate_full_name: str, completed_sections: str
) -> RecommendationOutput:
    structured_llm = llm.with_structured_output(RecommendationOutput)
    return structured_llm.invoke(
        [
            SystemMessage(
                content=recommendation_prompt.format(
                    job_description=job_description,
                    candidate_full_name=candidate_full_name,
                    completed_sections=completed_sections,
                )
            ),
            HumanMessage(
                content="Write a recommendation on how good of a fit the candidate is for the job based on the provided information."
            ),
        ]
    )


@traceable(name="get_trait_evaluation")
def get_trait_evaluation(
    trait: str,
    trait_description: str,
    candidate_full_name: str,
    candidate_context: str,
    source_str: str,
    trait_type: str = "SCORE",  # Default to SCORE for backward compatibility
    value_type: str = None,
    min_value: float = None,
    max_value: float = None,
    categories: List[str] = None,
) -> TraitEvaluationOutput:
    """
    Evaluate a candidate on a specific trait.

    Args:
        trait: The name of the trait
        trait_description: Description of the trait and how to evaluate it
        candidate_full_name: The candidate's full name
        candidate_context: Basic context about the candidate
        source_str: String containing all relevant sources about the candidate
        trait_type: Type of trait (BOOLEAN, NUMERIC, SCORE, CATEGORICAL)
        value_type: For numeric traits, what the number represents (e.g. "years")
        min_value: For numeric traits, the minimum required value
        max_value: For numeric traits, the maximum value (if applicable)
        categories: For categorical traits, list of valid categories
    """
    structured_llm = llm.with_structured_output(TraitEvaluationOutput)

    # Build the evaluation prompt based on trait type
    type_specific_instructions = ""
    if trait_type == "BOOLEAN":
        type_specific_instructions = (
            "Evaluate if the candidate meets this requirement (true/false)."
        )
    elif trait_type == "NUMERIC":
        type_specific_instructions = f"Extract the specific {value_type} value. If a range is found, use the lower bound."
    elif trait_type == "SCORE":
        type_specific_instructions = "Rate the candidate from 0-10 on this trait."
    elif trait_type == "CATEGORICAL":
        categories_str = (
            ", ".join(categories) if categories else "any relevant category"
        )
        type_specific_instructions = (
            f"Determine which category best describes the candidate: {categories_str}"
        )

    return structured_llm.invoke(
        [
            SystemMessage(
                content=trait_evaluation_prompt.format(
                    section=trait,
                    trait_description=trait_description,
                    candidate_full_name=candidate_full_name,
                    candidate_context=candidate_context,
                    source_str=source_str,
                    trait_type=trait_type,
                    type_specific_instructions=type_specific_instructions,
                    value_type=value_type,
                    min_value=min_value,
                    max_value=max_value,
                    categories=categories,
                )
            ),
            HumanMessage(
                content="Evaluate the candidate on this trait based on the provided information."
            ),
        ]
    )


@traceable(name="get_reachout_message")
def get_reachout_message(
    name: str,
    job_description: str,
    sections: list[dict],
    citations: list[dict],
    format: str,
) -> str:
    sections_str = "\n".join(
        [f"{section['section']}: {section['content']} " for section in sections]
    )
    citations_str = "\n".join(
        [f"{citation['distilled_content']}" for citation in citations]
    )
    prompt = (
        reachout_message_prompt_linkedin
        if format == "linkedin"
        else reachout_message_prompt_email
    )
    output = llm.invoke(
        [
            SystemMessage(
                content=prompt.format(
                    name=name,
                    job_description=job_description,
                    sections=sections_str,
                    citations=citations_str,
                )
            )
        ]
        + [
            HumanMessage(
                content="Write a message to the candidate that is tailored to their profile and the information provided."
            )
        ]
    )
    return output.content
