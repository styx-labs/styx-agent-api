from pydantic import BaseModel
from typing import List


class Job(BaseModel):
    job_description: str
    key_traits: List[str]


class JobDescription(BaseModel):
    description: str


class Candidate(BaseModel):
    name: str = None
    context: str = None
    url: str = None


class ParaformEvaluateGraphPayload(BaseModel):
    candidate_context: str
    candidate_full_name: str
    number_of_queries: int


class ParaformEvaluateGraphLinkedinPayload(BaseModel):
    linkedin_url: str
    number_of_queries: int


class EvaluateGraphPayload(BaseModel):
    job_description: str
    candidate_context: str
    candidate_full_name: str
    key_traits: List[str]
    number_of_queries: int
