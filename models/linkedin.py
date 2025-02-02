"""
LinkedIn data models with standardized serialization.
"""

from typing import List, Optional
from datetime import date
from .serializable import SerializableModel
from .career import (
    CareerMetrics,
    FundingStage,
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

    def _determine_funding_stage(self, funding) -> FundingStage:
        """Helper method to determine funding stage from a funding round."""
        funding_type = funding.funding_type.lower() if funding.funding_type else ""

        if "ipo" in funding_type:
            return FundingStage.IPO
        elif "series d" in funding_type:
            return FundingStage.SERIES_D
        elif "series e" in funding_type:
            return FundingStage.SERIES_E
        elif "series f" in funding_type:
            return FundingStage.SERIES_F
        elif "series g" in funding_type:
            return FundingStage.SERIES_G
        elif "series h" in funding_type:
            return FundingStage.SERIES_H
        elif "series i" in funding_type:
            return FundingStage.SERIES_I
        elif "series j" in funding_type:
            return FundingStage.SERIES_J
        elif "series k" in funding_type:
            return FundingStage.SERIES_K
        elif "series c" in funding_type:
            return FundingStage.SERIES_C
        elif "series b" in funding_type:
            return FundingStage.SERIES_B
        elif "series a" in funding_type:
            return FundingStage.SERIES_A
        elif "pre seed" in funding_type:
            return FundingStage.PRE_SEED
        elif "seed" in funding_type:
            return FundingStage.SEED
        return FundingStage.UNKNOWN

    @property
    def funding_stage(self) -> FundingStage:
        """Get the current funding stage of the company."""
        if not self.funding_data:
            return FundingStage.UNKNOWN

        latest_funding = self.funding_data[-1]
        return self._determine_funding_stage(latest_funding)

    def get_funding_stage_at_date(self, target_date: date) -> FundingStage:
        """Get the company's funding stage at a specific date."""
        if not self.funding_data:
            return FundingStage.UNKNOWN

        current_stage = FundingStage.UNKNOWN

        for funding in sorted(
            [f for f in self.funding_data if f.announced_date],
            key=lambda x: x.announced_date.get("year", 0) * 12
            + x.announced_date.get("month", 0),
        ):
            try:
                funding_date = date(
                    year=funding.announced_date.get("year", 1900),
                    month=funding.announced_date.get("month", 1),
                    day=1,
                )
                if funding_date <= target_date:
                    current_stage = self._determine_funding_stage(funding)
                else:
                    break
            except (KeyError, ValueError, TypeError):
                continue

        return current_stage

    def get_funding_stages_between_dates(
        self, start_date: date, end_date: date = None, cutoff_date: date = None
    ) -> List[FundingStage]:
        """Get the sequence of funding stages between two dates.

        Args:
            start_date: Start date of the period
            end_date: End date of the period (defaults to today)
            cutoff_date: Optional date before which to ignore funding rounds
        """
        if not self.funding_data:
            return [FundingStage.UNKNOWN]

        end_date = end_date or date.today()
        relevant_rounds = []

        # Filter funding data by cutoff date if provided
        valid_funding = [
            f
            for f in self.funding_data
            if f.announced_date
            and (
                not cutoff_date
                or date(
                    year=f.announced_date.get("year", 1900),
                    month=f.announced_date.get("month", 1),
                    day=1,
                )
                >= cutoff_date
            )
        ]

        if not valid_funding:
            return [FundingStage.UNKNOWN]

        # Get initial stage from valid funding rounds
        current_stage = self.get_funding_stage_at_date(start_date)

        for funding in sorted(
            valid_funding,
            key=lambda x: x.announced_date.get("year", 0) * 12
            + x.announced_date.get("month", 0),
        ):
            try:
                funding_date = date(
                    year=funding.announced_date.get("year", 1900),
                    month=funding.announced_date.get("month", 1),
                    day=1,
                )
                if start_date < funding_date <= end_date:
                    stage = self._determine_funding_stage(funding)
                    if stage != current_stage:
                        relevant_rounds.append(stage)
                        current_stage = stage
            except (KeyError, ValueError, TypeError):
                continue

        return [current_stage] + relevant_rounds if relevant_rounds else [current_stage]


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
    experience_tags: Optional[List[str]] = None

    @property
    def funding_stages_during_tenure(self) -> List[FundingStage]:
        """Calculate the funding stages of the company during this person's tenure."""
        if not self.company_data or not self.starts_at:
            return [FundingStage.UNKNOWN]

        # Calculate cutoff date (2 years before start date)
        two_years_before = date(
            year=self.starts_at.year - 2, month=self.starts_at.month, day=1
        )

        return self.company_data.get_funding_stages_between_dates(
            self.starts_at, self.ends_at, cutoff_date=two_years_before
        )

    @property
    def duration_months(self) -> Optional[int]:
        """Calculate the duration of this experience in months."""
        if not self.starts_at:
            return None

        end_date = self.ends_at or date.today()
        months = (end_date.year - self.starts_at.year) * 12 + (
            end_date.month - self.starts_at.month
        )
        return max(0, months)

    def dict(self, *args, **kwargs) -> dict:
        """Override dict to exclude company_data by default and include calculated fields."""
        exclude = kwargs.get("exclude", set())
        if "company_data" not in exclude:
            exclude.add("company_data")
        kwargs["exclude"] = exclude

        # Get base dictionary
        d = super().dict(*args, **kwargs)

        # Add calculated fields
        d["duration_months"] = self.duration_months
        d["funding_stages_during_tenure"] = [
            stage.value for stage in self.funding_stages_during_tenure
        ]

        return d


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
        """Override dict to handle nested serialization properly."""
        # Get base dictionary
        d = super().dict(*args, **kwargs)

        # Manually serialize experiences to ensure their custom dict() method is called
        d["experiences"] = [exp.dict(*args, **kwargs) for exp in self.experiences]

        return d
