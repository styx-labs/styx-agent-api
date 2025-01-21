"""
LinkedIn data models.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class AILinkedinJobDescription(BaseModel):
    role_summary: str
    skills: List[str]
    requirements: List[str]
    sources: List[str]


class LinkedInExperience(BaseModel):
    title: str
    company: str
    description: Optional[str] = None
    starts_at: Optional[date] = None
    ends_at: Optional[date] = None
    location: Optional[str] = None
    summarized_job_description: Optional[AILinkedinJobDescription] = None


class LinkedInEducation(BaseModel):
    school: Optional[str] = None
    degree_name: Optional[str] = None
    field_of_study: Optional[str] = None
    starts_at: Optional[date] = None
    ends_at: Optional[date] = None


class LinkedInProfile(BaseModel):
    full_name: str
    occupation: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    public_identifier: Optional[str] = None
    experiences: List[LinkedInExperience] = []
    education: List[LinkedInEducation] = []

    def to_context_string(self) -> str:
        """Convert the profile to a formatted string context."""
        context = f"Name: {self.full_name}\n"
        if self.occupation:
            context += f"Occupation: {self.occupation}\n"
        if self.headline:
            context += f"Headline: {self.headline}\n"
        if self.summary:
            context += f"Summary: {self.summary}\n"
        if self.city:
            context += f"City: {self.city}\n"

        for exp in self.experiences:
            context += f"Experience: {exp.title} at {exp.company}"
            if exp.description:
                context += f" - {exp.description}"
            context += "\n"

        for edu in self.education:
            context += (
                f"Education: {edu.school}; {edu.degree_name} in {edu.field_of_study}\n"
            )

        return context

    @classmethod
    def from_dict(cls, data: dict) -> "LinkedInProfile":
        return cls(**data)
