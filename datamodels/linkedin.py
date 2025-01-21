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

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            title=data["title"],
            company=data["company"],
            description=data["description"],
            starts_at=data["starts_at"],
            ends_at=data["ends_at"],
            location=data["location"],
            summarized_job_description=AILinkedinJobDescription.from_dict(
                data["summarized_job_description"]
            )
            if data["summarized_job_description"]
            else None,
        )


class LinkedInEducation(BaseModel):
    school: str
    degree_name: Optional[str] = None
    field_of_study: Optional[str] = None
    starts_at: Optional[date] = None
    ends_at: Optional[date] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            school=data["school"],
            degree_name=data["degree_name"],
            field_of_study=data["field_of_study"],
            starts_at=data["starts_at"],
            ends_at=data["ends_at"],
        )


class LinkedInProfile(BaseModel):
    full_name: str
    occupation: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    public_identifier: str
    experiences: List[LinkedInExperience] = []
    education: List[LinkedInEducation] = []

    def to_context_string(self) -> str:
        """Convert the profile to a formatted string context."""
        context = ""

        if self.occupation:
            context += f"Current Occupation: {self.occupation}\n"
            context += "\n---------\n"
        if self.headline:
            context += f"Headline: {self.headline}\n"
            context += "\n---------\n"
        if self.summary:
            context += f"Summary: {self.summary}\n"
            context += "\n---------\n"
        if self.city and self.country:
            context += f"Location of this candidate: {self.city}, {self.country}\n"
            context += "\n---------\n"

        for exp in self.experiences:
            context += f"Experience: {exp.title} at {exp.company}\n"
            if exp.description:
                context += f"Description: {exp.description}\n"
            if exp.starts_at:
                context += f"Start Year: {exp.starts_at.year}\n"
                context += f"Start Month: {exp.starts_at.month}\n"
            if exp.ends_at:
                context += f"End Year: {exp.ends_at.year}\n"
                context += f"End Month: {exp.ends_at.month}\n"
            if exp.summarized_job_description:
                context += (
                    f"Role Summary: {exp.summarized_job_description.role_summary}\n"
                )
                context += f"Skills: {exp.summarized_job_description.skills}\n"
                context += (
                    f"Requirements: {exp.summarized_job_description.requirements}\n"
                )
            context += "\n---------\n"

        for edu in self.education:
            if edu.school and edu.degree_name and edu.field_of_study:
                context += f"Education: {edu.school}; {edu.degree_name} in {edu.field_of_study}\n"
                if edu.starts_at:
                    context += f"Start Year: {edu.starts_at.year}\n"
                    context += f"Start Month: {edu.starts_at.month}\n"
                if edu.ends_at:
                    context += f"End Year: {edu.ends_at.year}\n"
                    context += f"End Month: {edu.ends_at.month}\n"
                context += "\n---------\n"

        return context

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            full_name=data["full_name"],
            occupation=data["occupation"],
            headline=data["headline"],
            summary=data["summary"],
            city=data["city"],
            country=data["country"],
            public_identifier=data["public_identifier"],
            experiences=data["experiences"],
            education=data["education"],
        )

    @classmethod
    def from_dict(cls, data: dict) -> "LinkedInProfile":
        return cls(**data)
