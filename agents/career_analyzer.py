"""
Career analysis functions for LinkedIn profiles.
"""

from typing import List
from datamodels.linkedin import LinkedInProfile, LinkedInExperience
from datamodels.career import (
    CareerMetrics,
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
    # tech_stacks = extract_tech_stacks(profile.experiences)
    # career_tags = generate_career_tags(profile.experiences, avg_tenure_months)

    return CareerMetrics(
        total_experience_months=total_months,
        average_tenure_months=avg_tenure_months,
        current_tenure_months=current_tenure_months,
        tech_stacks=[],
        career_tags=[],
    )


def is_professional_experience(exp) -> bool:
    """
    Determine if an experience is a professional role (excluding internships and education).
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
        ]
    ):
        return False
    # Exclude academic/research assistant positions typically held during education
    if any(
        term in title_lower
        for term in ["research assistant", "teaching assistant", "graduate assistant"]
    ):
        return False

    return True


def calculate_total_months(experiences: List[LinkedInExperience]) -> int:
    """Calculate total months of professional experience."""
    return sum(
        exp.duration_months or 0
        for exp in experiences
        if is_professional_experience(exp)
    )


def calculate_average_tenure_months(experiences: List[LinkedInExperience]) -> int:
    """Calculate average months spent at each company."""
    professional_experiences = [
        exp for exp in experiences if is_professional_experience(exp)
    ]
    if not professional_experiences:
        return 0

    tenures = [exp.duration_months or 0 for exp in professional_experiences]
    return round(sum(tenures) / len(tenures))


def calculate_current_tenure_months(experiences: List[LinkedInExperience]) -> int:
    """Calculate months spent at current company."""
    current_role = next(
        (
            exp
            for exp in experiences
            if not exp.ends_at and is_professional_experience(exp)
        ),
        None,
    )

    return current_role.duration_months if current_role else 0


# def extract_tech_stacks(experiences: List[LinkedInExperience]) -> List[str]:
#     """Extract technical skills and technologies from experience."""
#     tech_stacks = set()

#     for exp in experiences:
#         text_to_analyze = []

#         if exp.description:
#             text_to_analyze.append(exp.description)
#         if exp.title:
#             text_to_analyze.append(exp.title)
#         if exp.summarized_job_description:
#             text_to_analyze.append(exp.summarized_job_description.role_summary)
#             text_to_analyze.extend(exp.summarized_job_description.skills)
#             text_to_analyze.extend(exp.summarized_job_description.requirements)

#         combined_text = " ".join(text_to_analyze).lower()
#         detected_stacks = TechStackPatterns.detect_tech_stacks(combined_text)
#         tech_stacks.update(stack.value for stack in detected_stacks)

#     return sorted(list(tech_stacks))


# def generate_career_tags(experiences, avg_tenure_months: int) -> Set[str]:
#     """Generate career-related tags based on experience."""
#     tags = set()

#     # Track companies and titles for promotion analysis
#     company_titles = {}  # company -> list of titles
#     company_count = len(
#         {
#             exp.company
#             for exp in experiences
#             if exp.company and is_professional_experience(exp)
#         }
#     )

#     for exp in experiences:
#         if not exp.title or not is_professional_experience(exp):
#             continue

#         title = exp.title.lower()

#         # Track titles by company for promotion analysis
#         if exp.company:
#             if exp.company not in company_titles:
#                 company_titles[exp.company] = []
#             company_titles[exp.company].append(title)

#         # Add tech stack specific tags
#         if exp.summarized_job_description:
#             detected_stacks = TechStackPatterns.detect_tech_stacks(
#                 " ".join(
#                     [
#                         exp.summarized_job_description.role_summary,
#                         *exp.summarized_job_description.skills,
#                         *exp.summarized_job_description.requirements,
#                     ]
#                 ).lower()
#             )
#             for stack in detected_stacks:
#                 tags.add(f"{stack.value} Engineer")

#             # Add special combination tags
#             if (
#                 TechStack.BACKEND in detected_stacks
#                 and TechStack.ML_AI in detected_stacks
#             ):
#                 tags.add("ML Systems Engineer")
#             if (
#                 TechStack.INFRASTRUCTURE in detected_stacks
#                 and TechStack.ML_AI in detected_stacks
#             ):
#                 tags.add("MLOps Engineer")
#             if TechStack.DATA in detected_stacks and TechStack.ML_AI in detected_stacks:
#                 tags.add("ML Data Engineer")

#     # Career pattern analysis
#     years_of_experience = sum(calculate_total_months(experiences)) / 12

#     # Analyze promotions within companies
#     for company, titles in company_titles.items():
#         if len(titles) >= 3:
#             tags.add("Promoted Multiple Times")
#         elif len(titles) == 2:
#             tags.add("Promoted Once")

#     # Analyze job hopping and stability patterns
#     if avg_tenure_months < 18 and company_count >= 3:  # Less than 1.5 years average
#         tags.add("Frequent Job Changes")
#     elif avg_tenure_months >= 36:  # 3+ years average tenure
#         tags.add("High Average Tenure")

#     # Company diversity
#     if company_count >= 5:
#         tags.add("Diverse Company Experience")
#     elif company_count == 1 and years_of_experience >= 5:
#         tags.add("Single Company Focus")

#     return tags
