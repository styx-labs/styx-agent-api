"""
Career analysis functions for LinkedIn profiles.
"""

from typing import List, Set
from datetime import date
from datamodels.linkedin import LinkedInProfile, LinkedInCompany
from datamodels.career import (
    CareerMetrics,
    FundingStage,
    CompanyTier,
    TechStack,
    ExperienceStageMetrics,
    TechStackPatterns,
)


def analyze_career(profile: LinkedInProfile) -> CareerMetrics:
    """
    Analyze a LinkedIn profile and compute career metrics.
    Returns a CareerMetrics object containing the analysis.
    """
    # Calculate basic metrics in months
    total_months = calculate_total_months(profile.experiences)
    avg_tenure_months = calculate_average_tenure_months(profile.experiences)
    current_tenure_months = calculate_current_tenure_months(profile.experiences)

    # Extract technical information
    tech_stacks = extract_tech_stacks(profile.experiences)
    career_tags = generate_career_tags(profile.experiences)
    exp_by_stage = analyze_company_stages(profile.experiences)

    return CareerMetrics(
        total_experience_months=total_months,
        total_experience_years=round(total_months / 12, 1),
        average_tenure_months=avg_tenure_months,
        average_tenure_years=round(avg_tenure_months / 12, 1),
        current_tenure_months=current_tenure_months,
        current_tenure_years=round(current_tenure_months / 12, 1),
        tech_stacks=tech_stacks,
        career_tags=list(career_tags),
        experience_by_stage=exp_by_stage,
    )


def calculate_total_months(experiences) -> int:
    """Calculate total months of professional experience."""
    total_months = 0
    today = date.today()

    for exp in experiences:
        if not exp.starts_at:
            continue

        end_date = exp.ends_at or today
        months = (end_date.year - exp.starts_at.year) * 12 + (
            end_date.month - exp.starts_at.month
        )
        total_months += max(0, months)

    return total_months


def calculate_average_tenure_months(experiences) -> int:
    """Calculate average months spent at each company."""
    if not experiences:
        return 0

    tenures = []
    today = date.today()

    for exp in experiences:
        if not exp.starts_at:
            continue

        end_date = exp.ends_at or today
        months = (end_date.year - exp.starts_at.year) * 12 + (
            end_date.month - exp.starts_at.month
        )
        tenures.append(max(0, months))

    if not tenures:
        return 0

    return round(sum(tenures) / len(tenures))


def calculate_current_tenure_months(experiences) -> int:
    """Calculate months spent at current company."""
    current_role = next((exp for exp in experiences if not exp.ends_at), None)

    if not current_role or not current_role.starts_at:
        return 0

    today = date.today()
    months = (today.year - current_role.starts_at.year) * 12 + (
        today.month - current_role.starts_at.month
    )

    return max(0, months)


def extract_tech_stacks(experiences) -> List[str]:
    """Extract technical skills and technologies from experience."""
    tech_stacks = set()

    for exp in experiences:
        text_to_analyze = []

        if exp.description:
            text_to_analyze.append(exp.description)
        if exp.title:
            text_to_analyze.append(exp.title)
        if exp.summarized_job_description:
            text_to_analyze.append(exp.summarized_job_description.role_summary)
            text_to_analyze.extend(exp.summarized_job_description.skills)
            text_to_analyze.extend(exp.summarized_job_description.requirements)

        combined_text = " ".join(text_to_analyze).lower()
        detected_stacks = TechStackPatterns.detect_tech_stacks(combined_text)
        tech_stacks.update(stack.value for stack in detected_stacks)

    return sorted(list(tech_stacks))


def generate_career_tags(experiences) -> Set[str]:
    """Generate career-related tags based on experience."""
    tags = set()

    # Analyze titles and roles
    for exp in experiences:
        if not exp.title:
            continue

        title = exp.title.lower()

        # Leadership tags
        if any(
            role in title
            for role in ["lead", "head", "director", "manager", "vp", "chief"]
        ):
            tags.add("Leadership Experience")

        # Technical roles
        if any(role in title for role in ["engineer", "developer", "architect"]):
            tags.add("Technical")
        if "senior" in title or "sr" in title:
            tags.add("Senior Level")
        if "staff" in title:
            tags.add("Staff Level")

        # Add tech stack specific tags
        if exp.summarized_job_description:
            detected_stacks = TechStackPatterns.detect_tech_stacks(
                " ".join(
                    [
                        exp.summarized_job_description.role_summary,
                        *exp.summarized_job_description.skills,
                        *exp.summarized_job_description.requirements,
                    ]
                ).lower()
            )
            for stack in detected_stacks:
                tags.add(f"{stack.value} Engineer")

            # Add special combination tags
            if (
                TechStack.BACKEND in detected_stacks
                and TechStack.ML_AI in detected_stacks
            ):
                tags.add("ML Systems Engineer")
            if (
                TechStack.INFRASTRUCTURE in detected_stacks
                and TechStack.ML_AI in detected_stacks
            ):
                tags.add("MLOps Engineer")
            if TechStack.DATA in detected_stacks and TechStack.ML_AI in detected_stacks:
                tags.add("ML Data Engineer")

    return tags


def analyze_company_stages(experiences) -> List[ExperienceStageMetrics]:
    """Analyze experience by company stage."""
    stage_metrics = []
    today = date.today()

    for exp in experiences:
        if not exp.starts_at or not exp.company:
            continue

        funding_stage = FundingStage.UNKNOWN
        company_tier = CompanyTier.STARTUP

        if exp.company_data:
            funding_stage = determine_funding_stage(exp.company_data)
            company_tier = determine_company_tier(exp.company_data)

        duration_months = ((exp.ends_at or today).year - exp.starts_at.year) * 12 + (
            (exp.ends_at or today).month - exp.starts_at.month
        )

        stage_metrics.append(
            ExperienceStageMetrics(
                company_name=exp.company,
                funding_stage=funding_stage,
                joined_at=exp.starts_at,
                left_at=exp.ends_at,
                duration_months=max(0, duration_months),
                company_tier=company_tier,
            )
        )

    return stage_metrics


def determine_funding_stage(company_data: LinkedInCompany) -> FundingStage:
    """Determine company's funding stage based on available data."""
    if not company_data.funding_data:
        return FundingStage.UNKNOWN

    latest_funding = company_data.funding_data[-1]
    funding_type = (
        latest_funding.funding_type.lower() if latest_funding.funding_type else ""
    )

    if "ipo" in funding_type:
        return FundingStage.IPO
    elif "series d" in funding_type or "series e" in funding_type:
        return FundingStage.SERIES_D_PLUS
    elif "series c" in funding_type:
        return FundingStage.SERIES_C
    elif "series b" in funding_type:
        return FundingStage.SERIES_B
    elif "series a" in funding_type:
        return FundingStage.SERIES_A
    elif "seed" in funding_type:
        return FundingStage.SEED

    return FundingStage.UNKNOWN


def determine_company_tier(company_data: LinkedInCompany) -> CompanyTier:
    """Determine company tier based on size and funding."""
    if not company_data.company_size:
        return CompanyTier.STARTUP

    size = company_data.company_size[0] if company_data.company_size[0] else 0

    if size > 10000:
        return CompanyTier.BIG_TECH
    elif size > 1000:
        return CompanyTier.GROWTH
    elif size > 100:
        return CompanyTier.ENTERPRISE
    else:
        return CompanyTier.STARTUP
