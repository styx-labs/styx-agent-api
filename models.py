from pydantic import BaseModel
from typing import List


class Job(BaseModel):
    job_description: str
    key_traits: List[str]
    job_title: str
    company_name: str


class JobDescription(BaseModel):
    description: str


class Candidate(BaseModel):
    name: str = None
    context: str = None
    url: str = None
    number_of_queries: int = 5
    confidence_threshold: float = 0.5


class HeadlessEvaluatePayload(Candidate):
    job_description: str = None


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
