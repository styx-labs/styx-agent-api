from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field


class TraitType(str, Enum):
    BOOLEAN = "boolean"
    NUMERIC = "numeric"
    SCORE = "score"
    CATEGORICAL = "categorical"

    @classmethod
    def _missing_(cls, value: str):
        # Handle uppercase values by converting to lowercase
        if isinstance(value, str):
            return cls(value.lower())
        return None


class KeyTrait(BaseModel):
    trait: str
    description: str
    trait_type: TraitType
    value_type: Optional[str] = None  # e.g. "years", "location", "tech_stack"
    min_value: Optional[float] = None  # for numeric traits
    max_value: Optional[float] = None  # for numeric traits
    categories: Optional[List[str]] = None  # for categorical traits
    required: bool = True


class Job(BaseModel):
    job_description: str
    key_traits: List[KeyTrait]
    job_title: str
    company_name: str


class JobDescription(BaseModel):
    description: str


class Candidate(BaseModel):
    name: str = None
    context: str = None
    url: str
    public_identifier: str = None
    number_of_queries: int = 5
    confidence_threshold: float = 0.5


class HeadlessEvaluatePayload(Candidate):
    job_description: str = None


class ReachoutPayload(BaseModel):
    format: str


class HeadlessReachoutPayload(BaseModel):
    name: str
    job_description: str
    sections: list[dict]
    citations: list[dict]


class ParaformEvaluateGraphPayload(BaseModel):
    candidate_context: str
    candidate_full_name: str
    number_of_roles: int


class ParaformEvaluateGraphLinkedinPayload(BaseModel):
    linkedin_url: str
    number_of_queries: int


class BulkLinkedInPayload(BaseModel):
    urls: List[str]


class GetEmailPayload(BaseModel):
    linkedin_profile_url: str
