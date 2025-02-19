"""
LinkedIn data models with standardized serialization.
"""

import re
from datetime import date
from .serializable import SerializableModel
from .career import (
    CareerMetrics,
    FundingStage,
)
from services.firestore import db


class CompanyLocation(SerializableModel):
    """Model for company location data."""

    city: str | None = None
    country: str | None = None
    is_hq: bool = False
    line_1: str | None = None
    postal_code: str | None = None
    state: str | None = None


class AffiliatedCompany(SerializableModel):
    """Model for affiliated company data."""

    industry: str | None = None
    link: str | None = None
    location: str | None = None
    name: str | None = None


class CompanyUpdate(SerializableModel):
    """Model for company update data."""

    article_link: str | None = None
    image: str | None = None
    posted_on: dict | None = None
    text: str | None = None
    total_likes: int | None = None


class Investor(SerializableModel):
    """Model for investor data."""

    linkedin_profile_url: str | None = None
    name: str | None = None
    type: str | None = None


class Funding(SerializableModel):
    """Model for funding round data."""

    funding_type: str | None = None
    money_raised: int | None = None
    announced_date: dict | None = None
    number_of_investors: int | None = None
    investor_list: list[Investor] = []


class LinkedInCompany(SerializableModel):
    """Model for LinkedIn company profile data."""

    company_name: str
    description: str | None = None
    website: str | None = None
    industry: str | None = None
    company_size: list[int | None] | None = None
    company_size_on_linkedin: int | None = None
    company_type: str | None = None
    founded_year: int | None = None
    specialties: list[str] = []
    locations: list[CompanyLocation] = []
    hq: CompanyLocation | None = None
    follower_count: int | None = None
    profile_pic_url: str | None = None
    background_cover_image_url: str | None = None
    tagline: str | None = None
    universal_name_id: str | None = None
    linkedin_internal_id: str | None = None
    search_id: str | None = None
    updates: list[CompanyUpdate] = []
    similar_companies: list[AffiliatedCompany] = []
    affiliated_companies: list[AffiliatedCompany] = []
    funding_data: list[Funding] | None = None

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
    ) -> list[FundingStage]:
        """Get the sequence of funding stages between two dates.

        Args:
            start_date: Start date of the period
            end_date: End date of the period (defaults to today)
            cutoff_date: Optional date before which to ignore funding rounds
        """
        if not self.funding_data:
            return []

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

        return list(dict.fromkeys([current_stage] + relevant_rounds))


class AILinkedinJobDescription(SerializableModel):
    role_summary: str
    skills: list[str]
    requirements: list[str]
    sources: list[str]


class LinkedInExperience(SerializableModel):
    title: str | None
    company: str | None
    description: str | None
    starts_at: date | None
    ends_at: date | None
    location: str | None
    company_linkedin_profile_url: str | None
    company_data: LinkedInCompany | None = None
    summarized_job_description: AILinkedinJobDescription | None = None
    experience_tags: list[str] | None = None

    @property
    def funding_stages_during_tenure(self) -> list[FundingStage] | None:
        """Calculate the funding stages of the company during this person's tenure."""
        if (
            not self.company_linkedin_profile_url
            or not self.company_data
            or not self.starts_at
        ):
            return []

        if not self.company_data and "school" not in self.company_linkedin_profile_url:
            company_id = re.search(
                r"linkedin\.com/company/([^/?]+)", self.company_linkedin_profile_url
            ).group(1)
            company_data = db.collection("companies").document(company_id).get()

            if company_data:
                self.company_data = LinkedInCompany(**company_data.to_dict())

        # Calculate cutoff date (2 years before start date)
        two_years_before = date(
            year=self.starts_at.year - 2, month=self.starts_at.month, day=1
        )

        return self.company_data.get_funding_stages_between_dates(
            self.starts_at, self.ends_at, cutoff_date=two_years_before
        )

    @property
    def duration_months(self) -> int | None:
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
        if self.company_data and "company_data" not in exclude:
            exclude.add("company_data")
        kwargs["exclude"] = exclude

        # Get base dictionary
        d = super().dict(*args, **kwargs)

        # Add calculated fields
        d["duration_months"] = self.duration_months
        if self.funding_stages_during_tenure:
            d["funding_stages_during_tenure"] = [
                stage.value for stage in self.funding_stages_during_tenure
            ]

        return d


class LinkedInEducation(SerializableModel):
    school: str | None = None
    degree_name: str | None = None
    field_of_study: str | None = None
    starts_at: date | None = None
    ends_at: date | None = None
    school_linkedin_profile_url: str | None = None
    logo_url: str | None = None

    @property
    def school_id(self) -> str | None:
        """Get the LinkedIn school ID."""
        from agents.constants import extract_school_id

        if (
            self.school_linkedin_profile_url
            and "school" not in self.school_linkedin_profile_url
        ):
            if self.logo_url:
                match = re.search(r"/proxycurl/company/([^/]+)/", self.logo_url)
                return match.group(1) if match else None
            return None
        return extract_school_id(self.school_linkedin_profile_url)

    @property
    def university_tier(self) -> str | None:
        """Get the ranking tier of the university."""
        from agents.constants import get_university_tier_by_id

        if not self.school_id:
            return "other"
        return get_university_tier_by_id(self.school_id)

    def dict(self, *args, **kwargs) -> dict:
        """Override dict to include calculated fields."""
        d = super().dict(*args, **kwargs)
        d["university_tier"] = self.university_tier
        d["school_id"] = self.school_id
        return d


class LinkedInProfile(SerializableModel):
    full_name: str
    occupation: str | None
    headline: str | None
    summary: str | None
    city: str | None
    country: str | None
    public_identifier: str
    experiences: list[LinkedInExperience] = []
    education: list[LinkedInEducation] = []
    career_metrics: CareerMetrics | None = None

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
        d["education"] = [edu.dict(*args, **kwargs) for edu in self.education]

        return d
