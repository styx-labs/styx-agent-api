"""
LinkedIn data models with standardized serialization.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, TypeVar, Type, Set
from datetime import date
from .base import SerializableModel
from .career import (
    CareerMetrics,
    FundingStage,
    CompanyTier,
    TechStack,
    ExperienceStageMetrics,
    TechStackPatterns,
)


class CompanyLocation(SerializableModel):
    """Model for company location data."""

    city: Optional[str] = None
    country: Optional[str] = None
    is_hq: Optional[bool] = False
    line_1: Optional[str] = None
    postal_code: Optional[str] = None
    state: Optional[str] = None


class AffiliatedCompany(SerializableModel):
    """Model for affiliated company data."""

    industry: Optional[str] = None
    link: str
    location: Optional[str] = None
    name: str


class CompanyUpdate(SerializableModel):
    """Model for company update data."""

    article_link: Optional[str] = None
    image: Optional[str] = None
    posted_on: Optional[dict] = None
    text: Optional[str] = None
    total_likes: Optional[int] = None


class Investor(SerializableModel):
    """Model for investor data."""

    linkedin_profile_url: Optional[str] = None
    name: str
    type: Optional[str] = None


class Funding(SerializableModel):
    """Model for funding round data."""

    funding_type: Optional[str] = None
    money_raised: Optional[int] = None
    announced_date: Optional[dict] = None
    number_of_investors: Optional[int] = None
    investor_list: List[Investor] = []


class LinkedInCompany(SerializableModel):
    """Model for LinkedIn company profile data from Proxycurl API."""

    company_name: str
    description: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[List[Optional[int]]] = None
    company_size_on_linkedin: Optional[int] = None
    company_type: Optional[str] = None
    founded_year: Optional[int] = None
    specialties: Optional[List[str]] = []
    locations: List[CompanyLocation] = []
    hq: Optional[CompanyLocation] = None
    follower_count: Optional[int] = None
    profile_pic_url: Optional[str] = None
    background_cover_image_url: Optional[str] = None
    tagline: Optional[str] = None
    universal_name_id: Optional[str] = None
    linkedin_internal_id: Optional[str] = None
    search_id: Optional[str] = None
    updates: List[CompanyUpdate] = []
    similar_companies: List[AffiliatedCompany] = []
    affiliated_companies: List[AffiliatedCompany] = []
    funding_data: Optional[List[Funding]] = None


class AILinkedinJobDescription(SerializableModel):
    role_summary: str
    skills: List[str]
    requirements: List[str]
    sources: List[str]


class LinkedInExperience(SerializableModel):
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    starts_at: Optional[date] = None
    ends_at: Optional[date] = None
    location: Optional[str] = None
    company_linkedin_profile_url: Optional[str] = None
    company_data: Optional[LinkedInCompany] = None
    summarized_job_description: Optional[AILinkedinJobDescription] = None

    def dict(self, *args, **kwargs) -> dict:
        """Override dict to exclude company_data by default"""
        exclude = kwargs.get("exclude", set())
        if "company_data" not in exclude:
            exclude.add("company_data")
        kwargs["exclude"] = exclude
        return super().dict(*args, **kwargs)


class LinkedInEducation(SerializableModel):
    school: str
    degree_name: Optional[str] = None
    field_of_study: Optional[str] = None
    starts_at: Optional[date] = None
    ends_at: Optional[date] = None


class LinkedInProfile(SerializableModel):
    full_name: str
    occupation: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    public_identifier: str
    experiences: List[LinkedInExperience] = []
    education: List[LinkedInEducation] = []
    career_metrics: Optional[CareerMetrics] = None

    def analyze_career(self) -> None:
        """
        Analyze the profile's career history and compute metrics.
        This method populates the career_metrics field with computed metrics.
        """
        from agents.career_analyzer import analyze_career

        self.career_metrics = analyze_career(self)

    def to_context_string(self) -> str:
        """Convert the profile to a formatted string context."""
        context = ""

        if self.occupation:
            context += f"Current Occupation: {self.occupation}\n\n---------\n"
        if self.headline:
            context += f"Headline: {self.headline}\n\n---------\n"
        if self.summary:
            context += f"Summary: {self.summary}\n\n---------\n"
        if self.city and self.country:
            context += f"Location of this candidate: {self.city}, {self.country}\n\n---------\n"

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

            if exp.company_data:
                company = exp.company_data
                context += "\nCompany Information:\n"
                if company.industry:
                    context += f"Industry: {company.industry}\n"
                if company.company_size:
                    context += f"Company Size: {company.company_size}\n"
                if company.description:
                    context += f"Company Description: {company.description}\n"
                if company.specialties:
                    context += (
                        f"Company Specialties: {', '.join(company.specialties)}\n"
                    )
                if company.company_type:
                    context += f"Company Type: {company.company_type}\n"
                if company.hq:
                    context += f"Headquarters: {company.hq.city}, {company.hq.state}, {company.hq.country}\n"

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

    def dict(self, *args, **kwargs) -> dict:
        """Override dict to exclude company_data from experiences by default"""
        exclude = kwargs.get("exclude", set())
        kwargs["exclude"] = exclude
        return super().dict(*args, **kwargs)
