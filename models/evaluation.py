from typing import Union, List, Dict
from typing_extensions import TypedDict
from .base import SerializableModel, KeyTrait
from .linkedin import LinkedInProfile


class KeyTraitsOutput(SerializableModel):
    """Output from key traits extraction"""

    key_traits: List[KeyTrait]
    job_title: str
    company_name: str


class TraitEvaluationOutput(SerializableModel):
    """Output from trait evaluation"""

    value: Union[bool, int]  # Can be boolean, score (0-10)
    evaluation: str


class HeadlessEvaluationOutput(SerializableModel):
    """Output from headless evaluation"""

    value: int
    evaluation: str


class EvaluationInputState(TypedDict):
    """Input state for evaluation"""

    job_description: str
    candidate_context: str
    candidate_profile: LinkedInProfile
    candidate_full_name: str
    key_traits: List[KeyTrait]
    number_of_queries: int
    confidence_threshold: float
    search_mode: bool
    ideal_profiles: List[str]
    custom_instructions: str


class CachedEvaluationInputState(TypedDict):
    """Input state for cached evaluation"""

    source_str: str
    job_description: str
    candidate_context: str
    candidate_profile: LinkedInProfile
    candidate_full_name: str
    key_traits: List[KeyTrait]
    citations: List[Dict]
    ideal_profiles: List[str]
    custom_instructions: str


class EvaluationOutputState(TypedDict):
    """Output state from evaluation"""

    citations: List[Dict]
    sections: List[Dict]
    summary: str
    required_met: int
    optional_met: int
    source_str: str
    candidate_profile: LinkedInProfile
    fit: int
