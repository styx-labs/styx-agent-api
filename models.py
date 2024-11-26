from pydantic import BaseModel
from typing import List, Optional

class Analysis(BaseModel):
    job_description: str
    key_traits: List[str]
    num_candidates: int
    school_list: Optional[List[str]] = None
    location_list: Optional[List[str]] = None
    graduation_year_upper_bound: Optional[str] = None
    graduation_year_lower_bound: Optional[str] = None

class JobDescription(BaseModel):
    description: str
