"""
Career analysis functions for LinkedIn profiles.
"""

from typing import List
from models.linkedin import LinkedInProfile, LinkedInExperience, LinkedInEducation
from models.career import (
    CareerMetrics,
)
from .constants import unicorns, big_tech, quant


def analyze_career(profile: LinkedInProfile) -> CareerMetrics:
    """
    Analyze a LinkedIn profile and compute career metrics.
    Returns a CareerMetrics object containing the analysis.
    """
    # Filter professional experiences once
    professional_experiences = [
        exp
        for exp in profile.experiences
        if is_professional_experience(exp, profile.education)
    ]

    # Calculate basic metrics in months
    total_months = calculate_total_months(professional_experiences)
    avg_tenure_months = calculate_average_tenure_months(professional_experiences)
    current_tenure_months = calculate_current_tenure_months(professional_experiences)

    # Generate career tags
    career_tags = []
    career_tags.extend(
        generate_tenure_tags(professional_experiences, avg_tenure_months)
    )
    career_tags.extend(generate_promotion_tags(professional_experiences))

    # Generate experience tags
    experience_tags = generate_experience_tags(professional_experiences)

    return CareerMetrics(
        total_experience_months=total_months,
        average_tenure_months=avg_tenure_months,
        current_tenure_months=current_tenure_months,
        tech_stacks=[],
        career_tags=career_tags,
        experience_tags=experience_tags,
    )


def is_professional_experience(
    exp: LinkedInExperience, education: List[LinkedInEducation]
) -> bool:
    """
    Determine if an experience is a professional role (excluding internships, education,
    and any experience that overlaps with education periods).
    """
    if not exp.title:
        return False

    title_lower = exp.title.lower()

    # Exclude internships and co-ops
    if any(
        term in title_lower
        for term in [
            "intern",
            "internship",
            "co-op",
            "coop",
            "trainee",
            "fellow",
            "scholar",
            "student",
            "summer",
        ]
    ):
        return False
    # Exclude academic/research assistant positions typically held during education
    if any(
        term in title_lower
        for term in ["research assistant", "teaching assistant", "graduate assistant"]
    ):
        return False

    if (
        exp.company_linkedin_profile_url
        and "school" in exp.company_linkedin_profile_url
    ):
        return False

    # # Check if experience overlaps with any education period
    # for edu in education:
    #     if not edu.starts_at or not exp.starts_at:
    #         continue

    #     edu_end = edu.ends_at or edu.starts_at
    #     exp_end = exp.ends_at or exp.starts_at

    #     # Check for overlap between education and experience periods
    #     if exp.starts_at <= edu_end and exp_end >= edu.starts_at:
    #         return False

    return True


def calculate_total_months(professional_experiences: List[LinkedInExperience]) -> int:
    """
    Calculate total months of professional experience, accounting for overlapping roles.
    Returns the number of unique months worked across all professional experiences.
    """
    if not professional_experiences:
        return 0

    # Sort experiences by start date
    sorted_experiences = sorted(
        [exp for exp in professional_experiences if exp.starts_at],
        key=lambda x: x.starts_at,
    )
    if not sorted_experiences:
        return 0

    total_months = 0
    current_period_start = sorted_experiences[0].starts_at
    current_period_end = (
        sorted_experiences[0].ends_at or sorted_experiences[0].starts_at
    )

    # Process each experience
    for exp in sorted_experiences[1:]:
        exp_end = exp.ends_at or exp.starts_at

        if exp.starts_at > current_period_end:
            # There's a gap, so add the current period to total and start a new one
            months = (current_period_end.year - current_period_start.year) * 12 + (
                current_period_end.month - current_period_start.month
            )
            total_months += max(0, months)
            current_period_start = exp.starts_at
            current_period_end = exp_end
        else:
            # Periods overlap or are adjacent, extend current period if needed
            current_period_end = max(current_period_end, exp_end)

    # Add the final period
    final_months = (current_period_end.year - current_period_start.year) * 12 + (
        current_period_end.month - current_period_start.month
    )
    total_months += max(0, final_months)

    return total_months


def calculate_average_tenure_months(
    professional_experiences: List[LinkedInExperience],
) -> int:
    """Calculate average months spent at each company."""
    if not professional_experiences:
        return 0

    tenures = [exp.duration_months or 0 for exp in professional_experiences]
    return round(sum(tenures) / len(tenures))


def calculate_current_tenure_months(
    professional_experiences: List[LinkedInExperience],
) -> int:
    """Calculate months spent at current company."""
    current_role = next(
        (exp for exp in professional_experiences if not exp.ends_at),
        None,
    )

    return current_role.duration_months if current_role else 0


def generate_tenure_tags(
    professional_experiences: List[LinkedInExperience], avg_tenure_months: int
) -> List[str]:
    """Generate tags based on tenure patterns and company diversity."""
    tags = []

    # Count professional positions and unique companies
    professional_positions = len(professional_experiences)
    company_count = len(
        {exp.company for exp in professional_experiences if exp.company}
    )

    # Calculate total years of experience
    total_months = calculate_total_months(professional_experiences)
    years_of_experience = total_months / 12

    # Analyze tenure patterns
    if avg_tenure_months < 18 and professional_positions >= 3:
        tags.append("Low Average Tenure")
    elif avg_tenure_months >= 36:
        tags.append("High Average Tenure")

    # Analyze company diversity
    if company_count >= 5:
        tags.append("Diverse Company Experience")
    elif company_count == 1 and years_of_experience >= 5:
        tags.append("Single Company Focus")

    return tags


def generate_promotion_tags(
    professional_experiences: List[LinkedInExperience],
) -> List[str]:
    """Generate tags based on promotion patterns within companies."""
    tags = []

    # Track titles by company
    company_titles = {}
    for exp in professional_experiences:
        if not exp.company:
            continue

        if exp.company not in company_titles:
            company_titles[exp.company] = []
        company_titles[exp.company].append(exp.title)

    # Analyze promotions within companies
    for titles in company_titles.values():
        if len(titles) >= 3:
            tags.append("Multiple Promotions")
            break
        elif len(titles) == 2:
            tags.append("Single Promotion")
            break

    return tags


def generate_experience_tags(
    professional_experiences: List[LinkedInExperience],
) -> List[str]:
    """Generate tags based on company types and stages."""
    tags = set()
    companies_seen = set()

    for exp in professional_experiences:
        if not exp.company:
            continue

        company = exp.company.strip()
        if company in companies_seen:
            continue
        companies_seen.add(company)

        # Check company types
        if company in big_tech:
            tags.add("Worked at Big Tech")
        if company in unicorns:
            tags.add("Worked at Unicorn")
        if company in quant:
            tags.add("Worked at Quant Fund")

        # Add tags based on company funding stage
        # Note: This assumes the company object has funding_stage information
        if hasattr(exp, "funding_stages_during_tenure"):
            stages = [stage.lower() for stage in exp.funding_stages_during_tenure]
            if any(
                stage in {"pre-seed", "seed", "series a", "series b"}
                for stage in stages
            ):
                tags.add("Startup Experience")
            elif any(
                stage
                in {
                    "series c",
                    "series d",
                    "series e",
                    "series f",
                    "series g",
                    "series h",
                    "series i",
                    "series j",
                    "series k",
                }
                for stage in stages
            ):
                tags.add("Growth Company Experience")
            elif any(stage in {"ipo", "public"} for stage in stages):
                tags.add("Public Company Experience")

    return list(tags)
