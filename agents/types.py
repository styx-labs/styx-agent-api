"""
This file contains all the types for LLM calls and Langgraph state types.
"""

from typing import List, Annotated
from typing_extensions import TypedDict
import operator
from pydantic import BaseModel, Field


# All LLM output types
class KeyTraitsOutput(BaseModel):
    key_traits: list[str]


class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Query for web search.")


class QueriesOutput(BaseModel):
    queries: List[SearchQuery] = Field(
        description="List of search queries.",
    )


class ValidationOutput(BaseModel):
    confidence: float


class DistillSourceOutput(BaseModel):
    distilled_source: str


class RecommendationOutput(BaseModel):
    recommendation: str


class TraitEvaluationOutput(BaseModel):
    score: int
    evaluation: str


# Langgraph state types
class EvaluationState(TypedDict):
    source_str: str
    job_description: str
    candidate_context: str
    candidate_full_name: str
    key_traits: List[str]
    number_of_queries: int
    search_queries: list[SearchQuery]
    completed_sections: Annotated[list, operator.add]   # This is for parallelizing section writing
    validated_sources: Annotated[list, operator.add]   # This is for parallelizing source validation
    recommendation: str
    final_evaluation: str
    section: str   # This is for parallelizing section writing
    source: str   # This is for parallelizing source validation
    sources_dict: dict
    citations: list[dict]
    confidence_threshold: float


class EvaluationInputState(TypedDict):
    job_description: str
    candidate_context: str
    candidate_full_name: str
    key_traits: list[str]
    number_of_queries: int
    confidence_threshold: float


class EvaluationOutputState(TypedDict):
    citations: list[dict]
    sections: list[dict]
