"""
Career analysis functions for LinkedIn profiles.
"""

from typing import List, Dict, Tuple
from datetime import date
from collections import defaultdict
from models.linkedin import LinkedInProfile, LinkedInExperience
from models.career import CareerMetrics
from .constants import unicorns, big_tech, quant

# Constants for filtering experience titles
EXCLUDED_TITLE_TERMS = {
    "intern",
    "internship",
    "co-op",
    "coop",
    "trainee",
    "fellow",
    "scholar",
    "student",
    "summer",
    "advisor",
    "board member",
    "board advisor",
    "board observer",
    "board of director",
    "board of directors",
    "board of trustees",
    "board of trustees",
}
EXCLUDED_ASSISTANT_TERMS = {
    "research assistant",
    "teaching assistant",
    "graduate assistant",
}


def months_between(start: date, end: date) -> int:
    """Calculate full-month difference between two dates."""
    return (end.year - start.year) * 12 + (end.month - start.month)


def analyze_career(profile: LinkedInProfile) -> CareerMetrics:
    """Compute career metrics from a LinkedIn profile."""
    professional_experiences = [
        exp
        for exp in profile.experiences
        if is_professional_experience(exp, profile.education)
    ]

    total_months = calculate_total_months(professional_experiences)
    avg_tenure = calculate_average_tenure_months(professional_experiences)
    current_tenure = calculate_current_tenure_months(professional_experiences)

    career_tags = generate_tenure_tags(professional_experiences, avg_tenure)
    career_tags += generate_promotion_tags(professional_experiences)
    experience_tags = generate_experience_tags(professional_experiences)

    return CareerMetrics(
        total_experience_months=total_months,
        average_tenure_months=avg_tenure,
        current_tenure_months=current_tenure,
        tech_stacks=[],
        career_tags=career_tags,
        experience_tags=experience_tags,
    )


def is_professional_experience(exp: LinkedInExperience, education=None) -> bool:
    """
    Return True if the experience is a professional role, filtering out internships,
    assistant roles, and roles tied to educational institutions.
    """
    if not exp.title:
        return False

    title_lower = exp.title.lower()
    if any(term in title_lower for term in EXCLUDED_TITLE_TERMS):
        return False
    if any(term in title_lower for term in EXCLUDED_ASSISTANT_TERMS):
        return False

    if (
        exp.company_linkedin_profile_url
        and "school" in exp.company_linkedin_profile_url.lower()
    ):
        return False

    return True


def calculate_total_months(pro_exps: List[LinkedInExperience]) -> int:
    """
    Calculate unique months of experience by merging overlapping intervals
    across all roles (regardless of company).
    """
    intervals = []
    for exp in pro_exps:
        if exp.starts_at:
            start = exp.starts_at
            end = exp.ends_at or date.today()
            intervals.append((start, end))
    if not intervals:
        return 0

    intervals.sort(key=lambda i: i[0])
    merged = []
    current_start, current_end = intervals[0]

    for start, end in intervals[1:]:
        if start > current_end:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
        else:
            current_end = max(current_end, end)
    merged.append((current_start, current_end))

    return sum(max(0, months_between(s, e)) for s, e in merged)


def merge_experiences_by_company(
    pro_exps: List[LinkedInExperience],
) -> Dict[str, List[Tuple[date, date]]]:
    """
    Group experiences by company and merge adjacent/overlapping intervals.
    This ensures that multiple roles at the same company (when contiguous)
    are counted as one continuous tenure period.
    """
    company_intervals = defaultdict(list)
    for exp in pro_exps:
        if exp.company and exp.starts_at:
            start = exp.starts_at
            end = exp.ends_at or date.today()
            company_intervals[exp.company].append((start, end))

    merged: Dict[str, List[Tuple[date, date]]] = {}
    for company, intervals in company_intervals.items():
        intervals.sort(key=lambda x: x[0])
        merged_intervals = []
        current_start, current_end = intervals[0]
        for start, end in intervals[1:]:
            # Merge if intervals overlap or are adjacent (i.e. start <= current_end)
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                merged_intervals.append((current_start, current_end))
                current_start, current_end = start, end
        merged_intervals.append((current_start, current_end))
        merged[company] = merged_intervals
    return merged


def calculate_average_tenure_months(pro_exps: List[LinkedInExperience]) -> int:
    """
    Calculate average tenure (in months) per company after merging adjacent roles.
    This prevents penalizing candidates with multiple contiguous roles at the same company.
    """
    merged = merge_experiences_by_company(pro_exps)
    if not merged:
        return 0

    tenures = []
    for intervals in merged.values():
        # Sum merged intervals for each company
        total = sum(max(0, months_between(s, e)) for s, e in intervals)
        tenures.append(total)
    return round(sum(tenures) / len(tenures))


def calculate_current_tenure_months(pro_exps: List[LinkedInExperience]) -> int:
    """
    Calculate the current tenure (in months) for the active role(s) at a company.
    If multiple current roles exist in the same company, they are merged.
    For simplicity, if a candidate has current roles at multiple companies,
    return the longest current tenure.
    """
    current_by_company = {}
    today = date.today()
    for exp in pro_exps:
        if exp.company and exp.starts_at and not exp.ends_at:
            if exp.company in current_by_company:
                # Keep the earliest start date for the company
                current_by_company[exp.company] = min(
                    current_by_company[exp.company], exp.starts_at
                )
            else:
                current_by_company[exp.company] = exp.starts_at

    if not current_by_company:
        return 0

    current_tenures = [
        months_between(start, today) for start in current_by_company.values()
    ]
    return max(current_tenures) if current_tenures else 0


def generate_tenure_tags(
    pro_exps: List[LinkedInExperience], avg_tenure: int
) -> List[str]:
    """
    Generate tags based on tenure patterns and company diversity.
    """
    tags = []
    positions = len(pro_exps)
    companies = {exp.company for exp in pro_exps if exp.company}
    total_months = calculate_total_months(pro_exps)
    years_experience = total_months / 12

    if avg_tenure < 18 and positions >= 3:
        tags.append("Low Average Tenure")
    elif avg_tenure >= 36:
        tags.append("High Average Tenure")

    if len(companies) >= 5:
        tags.append("Diverse Company Experience")
    elif len(companies) == 1 and years_experience >= 5:
        tags.append("Single Company Focus")

    return tags


def generate_promotion_tags(pro_exps: List[LinkedInExperience]) -> List[str]:
    """
    Generate promotion tags based on number of titles held at each company.
    """
    multiple, single = False, False
    company_titles = {}
    for exp in pro_exps:
        if not exp.company:
            continue
        company_titles.setdefault(exp.company, []).append(exp.title)

    for titles in company_titles.values():
        if len(titles) >= 3:
            multiple = True
        elif len(titles) == 2:
            single = True

    if multiple:
        return ["Multiple Promotions"]
    if single:
        return ["Single Promotion"]
    return []


def generate_experience_tags(pro_exps: List[LinkedInExperience]) -> List[str]:
    """
    Generate tags based on company type and funding stage.
    """
    tags = set()
    seen_companies = set()

    for exp in pro_exps:
        if not exp.company:
            continue
        company = exp.company.strip()
        if company in seen_companies:
            continue
        seen_companies.add(company)

        if company in big_tech:
            tags.add("Worked at Big Tech")
        if company in unicorns:
            tags.add("Worked at Unicorn")
        if company in quant:
            tags.add("Worked at Quant Fund")

        stages = getattr(exp, "funding_stages_during_tenure", None)
        if stages:
            stages_lower = {s.lower() for s in stages}
            if stages_lower & {"pre-seed", "seed", "series a", "series b"}:
                tags.add("Startup Experience")
            elif stages_lower & {
                "series c",
                "series d",
                "series e",
                "series f",
                "series g",
                "series h",
                "series i",
                "series j",
                "series k",
            }:
                tags.add("Growth Company Experience")
            elif stages_lower & {"ipo", "public"}:
                tags.add("Public Company Experience")

    return list(tags)
