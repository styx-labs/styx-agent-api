"""
This file contains all the types for LLM calls and Langgraph state datamodels.
"""

from typing import Union
from typing_extensions import TypedDict
from pydantic import BaseModel
from models import KeyTrait
from datamodels.linkedin import LinkedInProfile


# All LLM output types
class KeyTraitsOutput(BaseModel):
    key_traits: list[KeyTrait]
    job_title: str
    company_name: str


class TraitEvaluationOutput(BaseModel):
    value: Union[bool, int]  # Can be boolean, score (0-10)
    evaluation: str
    trait_type: str  # The type of trait being evaluated (BOOLEAN, SCORE)


class EvaluationInputState(TypedDict):
    job_description: str
    candidate_context: str
    candidate_profile: LinkedInProfile
    candidate_full_name: str
    key_traits: list[KeyTrait]
    number_of_queries: int
    confidence_threshold: float
    search_mode: bool = True  # Controls whether to perform search or use LinkedIn-only mode


class CachedEvaluationInputState(TypedDict):
    source_str: str
    job_description: str
    candidate_context: str
    candidate_profile: LinkedInProfile
    candidate_full_name: str
    key_traits: list[KeyTrait]
    citations: list[dict]
    source_str: str


class EvaluationOutputState(TypedDict):
    citations: list[dict]
    sections: list[dict]
    summary: str
    overall_score: float
    source_str: str
    candidate_profile: LinkedInProfile
