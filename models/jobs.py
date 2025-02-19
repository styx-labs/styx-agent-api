from datetime import datetime
from pydantic import Field
from .serializable import SerializableModel
from .linkedin import LinkedInProfile
from typing import Literal

class KeyTrait(SerializableModel):
    """Represents a key trait required for a job"""

    trait: str
    description: str
    required: bool = True


class CalibratedProfiles(SerializableModel):
    """Represents a candidate to be calibrated"""

    url: str
    fit: Literal["good", "bad"] | None
    reasoning: str | None
    profile: LinkedInProfile | None
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
    key_traits: list[KeyTrait]
    calibrated_profiles: list[CalibratedProfiles] | None = None
    job_title: str
    company_name: str
    created_at: datetime = Field(default_factory=datetime.now)


class JobDescription(SerializableModel):
    """Represents a job description"""

    description: str
    calibrated_profiles: list[CalibratedProfiles] | None = None


class Candidate(SerializableModel):
    """Base candidate model"""

    name: str = None
    context: str = None
    url: str
    profile: LinkedInProfile | None = None
    public_identifier: str = None
    number_of_queries: int = 5
    confidence_threshold: float = 0.5
    search_mode: bool = True
    updated_at: datetime = Field(default_factory=datetime.now)
    favorite: bool = False
