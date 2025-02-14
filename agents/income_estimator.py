"""
Income estimation functions for career analysis.
"""

from .career_levels import (
    SALARY_RANGES,
    LOCATION_TIERS,
    COMPANY_TYPE_MULTIPLIERS,
    get_location_multiplier,
)


def get_company_multiplier(company_type: str) -> float:
    """
    Get the company type multiplier.

    Args:
        company_type: Type of company determined by LLM
            (big_tech, unicorn, growth, startup, standard)

    Returns:
        float: Company type multiplier
    """
    return COMPANY_TYPE_MULTIPLIERS.get(company_type.lower(), 1.0)


def estimate_income_range(
    level: str,
    track: str,
    location: str,  # Now expects a tier string (us_tier_1, eu_tier_2, etc.)
    country: str = None,  # Optional country for European locations
    company_type: str = "standard",  # Now expects LLM-determined type
) -> tuple[float, float, dict]:
    """
    Estimate total compensation range based on various factors.

    Args:
        level: Level code (L1-L6)
        track: Track code (ENG/EM/PM/SALES/DESIGN)
        location: Location tier from LLM analysis
        country: Country name (for European locations)
        company_type: Type of company from LLM analysis

    Returns:
        tuple[float, float, dict]: (min_total_comp, max_total_comp, comp_breakdown)
            where comp_breakdown contains:
            - base_salary: (min, max)
            - total_comp: (min, max)
            - location_tier: str
            - country: str
            - company_type: str
            - multipliers: dict with location and company multipliers
    """
    if track not in SALARY_RANGES or level not in SALARY_RANGES[track]:
        return (0, 0, {})

    # Get base salary range for track and level
    base_35th, base_50th, base_65th = SALARY_RANGES[track][level]

    # Get multipliers directly from the LLM-determined categories
    location_multiplier = get_location_multiplier(location, country)
    company_multiplier = get_company_multiplier(company_type)

    # Calculate ranges
    min_total = base_35th * location_multiplier * company_multiplier
    max_total = base_65th * location_multiplier * company_multiplier

    # For sales roles, base_65th represents OTE
    if track == "SALES":
        base_max = base_50th * location_multiplier * company_multiplier
        comp_breakdown = {
            "base_salary": (round(min_total, -3), round(base_max, -3)),
            "total_comp": (round(min_total, -3), round(max_total, -3)),
            "location_tier": location,
            "country": country,
            "company_type": company_type,
            "multipliers": {
                "location": location_multiplier,
                "company": company_multiplier,
            },
        }
    else:
        comp_breakdown = {
            "base_salary": (round(min_total, -3), round(max_total, -3)),
            "total_comp": (round(min_total, -3), round(max_total, -3)),
            "location_tier": location,
            "country": country,
            "company_type": company_type,
            "multipliers": {
                "location": location_multiplier,
                "company": company_multiplier,
            },
        }

    return (round(min_total, -3), round(max_total, -3), comp_breakdown)
