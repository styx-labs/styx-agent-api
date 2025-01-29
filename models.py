from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from datamodels.linkedin import LinkedInProfile


class KeyTrait(BaseModel):
    trait: str
    description: str
    required: bool = True


class EditKeyTraitsPayload(BaseModel):
    key_traits: List[KeyTrait]


class Job(BaseModel):
    job_description: str
    key_traits: List[KeyTrait]
    ideal_profiles: List[str] = None
    job_title: str
    company_name: str
    created_at: datetime = Field(default_factory=datetime.now)


class JobDescription(BaseModel):
    description: str
    ideal_profile_urls: List[str] = None


class Candidate(BaseModel):
    name: str = None
    context: str = None
    url: str
    profile: Optional[LinkedInProfile] = None
    public_identifier: str = None
    number_of_queries: int = 5
    confidence_threshold: float = 0.5
    search_mode: bool = True  # Controls whether to use search or LinkedIn-only mode
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
    search_mode: bool = True  # Controls whether to use search or LinkedIn-only mode


class GetEmailPayload(BaseModel):
    linkedin_profile_url: str


class CheckoutSessionRequest(BaseModel):
    planId: str


class TestTemplateRequest(BaseModel):
    format: str
    template_content: str
