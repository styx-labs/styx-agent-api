from pydantic import BaseModel
from typing import List


class Job(BaseModel):
    job_description: str
    key_traits: List[str]


class JobDescription(BaseModel):
    description: str


class Candidate(BaseModel):
    name: str
    context: str


class EvaluateGraphPayload(BaseModel):
    candidate_context: str
    candidate_full_name: str
    number_of_roles: int
