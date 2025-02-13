from typing import List, Optional, Literal
from datetime import datetime
from pydantic import Field
from .serializable import SerializableModel
from .linkedin import LinkedInProfile


class KeyTrait(SerializableModel):
    """Represents a key trait required for a job"""

    trait: str
    description: str
    required: bool = True


class PipelineFeedback(SerializableModel):
    """Represents a pipeline feedback"""

    feedback: str
    timestamp: datetime


class CalibratedProfiles(SerializableModel):
    """Represents a candidate to be calibrated"""

    url: str
    fit: Optional[Literal["good", "bad"]] = None
    reasoning: Optional[str] = None
    profile: Optional[LinkedInProfile] = None
    type: Literal["ideal", "pipeline"] = "pipeline"

    def __str__(self):
        output = ""
        if self.fit:
            output += f"Fit: {self.fit}\n"
        if self.reasoning:
            output += f"Reasoning: {self.reasoning}\n"
        if self.profile:
            output += f"Profile: {self.profile.to_context_string()}"
        return output.rstrip()


class Job(SerializableModel):
    """Represents a job posting"""

    job_description: str
    key_traits: List[KeyTrait]
    calibrated_profiles: Optional[list[CalibratedProfiles]] = None
    job_title: str
    company_name: str
    created_at: datetime = Field(default_factory=datetime.now)
    pipeline_feedback: Optional[list[PipelineFeedback]] = None


class JobDescription(SerializableModel):
    """Represents a job description"""

    description: str
    calibrated_profiles: List[CalibratedProfiles] = None


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
    favorite: bool = False
