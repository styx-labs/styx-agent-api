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
