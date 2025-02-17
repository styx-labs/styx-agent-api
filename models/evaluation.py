from typing import Union, Optional
from .serializable import SerializableModel
from .linkedin import LinkedInProfile
from .jobs import Job, KeyTrait


class KeyTraitsOutput(SerializableModel):
    """Output from key traits extraction"""

    key_traits: list[KeyTrait]
    job_title: str
    company_name: str


class EditKeyTraitsOutput(SerializableModel):
    """Output from key traits editing"""

    key_traits: list[KeyTrait]


class EditJobDescriptionOutput(SerializableModel):
    """Output from job description editing"""

    job_description: str


class TraitEvaluationOutput(SerializableModel):
    """Output from trait evaluation"""

    value: Union[bool, int]  # Can be boolean, score (0-10)
    evaluation: str


class SearchInputState(SerializableModel):
    """Input state for evaluation"""

    profile: LinkedInProfile
    job: Job
    number_of_queries: int
    confidence_threshold: float
    custom_instructions: Optional[str] = None


class EvaluationInputState(SerializableModel):
    """Input state for cached evaluation"""

    profile: LinkedInProfile
    job: Job
    source_str: str
    citations: list[dict]
    custom_instructions: Optional[str] = None


class EvaluationOutputState(SerializableModel):
    """Output state from evaluation"""

    citations: list[dict]
    sections: list[dict]
    summary: str
    required_met: int
    optional_met: int
    source_str: str
    fit: int
