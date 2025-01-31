from typing import List, Optional
from datetime import datetime
from pydantic import Field
from .serializable import SerializableModel
from .linkedin import LinkedInProfile


class KeyTrait(SerializableModel):
    """Represents a key trait required for a job"""

    trait: str
    description: str
    required: bool = True


class Job(SerializableModel):
    """Represents a job posting"""

    job_description: str
    key_traits: List[KeyTrait]
    ideal_profiles: List[str] = None
    job_title: str
    company_name: str
    created_at: datetime = Field(default_factory=datetime.now)


class JobDescription(SerializableModel):
    """Represents a job description"""

    description: str
    ideal_profile_urls: List[str] = None


class Candidate(SerializableModel):
    """Base candidate model"""

    name: str = None
    context: str = None
    url: str
    profile: Optional[LinkedInProfile] = None
    public_identifier: str = None
    number_of_queries: int = 5
    confidence_threshold: float = 0.5
    search_mode: bool = True
    updated_at: datetime = Field(default_factory=datetime.now)
