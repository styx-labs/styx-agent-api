from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class TraitType(str, Enum):
    BOOLEAN = "BOOLEAN"
    SCORE = "SCORE"

    @classmethod
    def _missing_(cls, value: str):
        # Handle uppercase values by converting to lowercase
        if isinstance(value, str):
            return cls(value.upper())
        return None


class KeyTrait(BaseModel):
    trait: str
    description: str
    trait_type: TraitType
    value_type: Optional[str] = None
    required: bool = True


class Job(BaseModel):
    job_description: str
    key_traits: List[KeyTrait]
    job_title: str
    company_name: str
    created_at: datetime = Field(default_factory=datetime.now)


class JobDescription(BaseModel):
    description: str


class Candidate(BaseModel):
    name: str = None
    context: str = None
    url: str
    public_identifier: str = None
    number_of_queries: int = 5
    confidence_threshold: float = 0.5
    updated_at: datetime = Field(default_factory=datetime.now)


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


class CheckoutSessionRequest(BaseModel):
    planId: str
