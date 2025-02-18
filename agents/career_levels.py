"""
Career level definitions and track-specific titles.
"""

from models.serializable import SerializableModel
from services.llms import llm_fast

# Career Track Constants
TRACKS = {
    "ENG": "Engineering",
    "EM": "Engineering Management",
    "PM": "Product Management",
    "SALES": "Sales",
    "DESIGN": "Design",
}

# Level titles by track
LEVEL_TITLES = {
    # Engineering (IC Track)
    "ENG": {
        "L1": [
            "entry level engineer",
            "new grad",
            "junior engineer",
            "associate engineer",
            "software engineer i",
        ],
        "L2": ["software engineer", "engineer ii", "mid level engineer"],
        "L3": [
            "senior engineer",
            "senior software engineer",
            "lead engineer",
            "tech lead",
        ],
        "L4": [
            "staff engineer",
            "staff software engineer",
            "founding engineer",
            "senior tech lead",
        ],
        "L5": [
            "principal engineer",
            "senior staff engineer",
            "distinguished staff engineer",
        ],
        "L6": ["distinguished engineer", "fellow", "senior principal engineer"],
    },
    # Engineering Management
    "EM": {
        "L1": ["team lead", "tech lead manager", "engineering team lead"],
        "L2": ["engineering manager", "development manager"],
        "L3": ["senior engineering manager", "group engineering manager"],
        "L4": ["director of engineering", "engineering director"],
        "L5": ["senior director of engineering", "vp of engineering"],
        "L6": ["svp of engineering", "cto", "chief technology officer"],
    },
    # Product Management
    "PM": {
        "L1": [
            "associate product manager",
            "junior product manager",
            "rotational product manager",
        ],
        "L2": ["product manager", "program manager"],
        "L3": ["senior product manager", "lead product manager"],
        "L4": ["group product manager", "principal product manager"],
        "L5": ["director of product", "head of product"],
        "L6": ["vp of product", "chief product officer", "cpo"],
    },
    # Sales
    "SALES": {
        "L1": [
            "sales development representative",
            "business development representative",
        ],
        "L2": ["account executive", "sales executive", "account manager"],
        "L3": ["senior account executive", "senior sales executive"],
        "L4": ["regional sales manager", "area sales director"],
        "L5": ["director of sales", "head of sales"],
        "L6": ["vp of sales", "chief revenue officer", "cro"],
    },
    # Design
    "DESIGN": {
        "L1": ["junior designer", "associate designer", "visual designer"],
        "L2": ["product designer", "ux designer", "ui designer"],
        "L3": ["senior designer", "senior product designer"],
        "L4": ["staff designer", "lead designer"],
        "L5": ["principal designer", "design director"],
        "L6": ["vp of design", "chief design officer", "cdo"],
    },
}


class CareerLevelAnalysis(SerializableModel):
    """Model for LLM analysis of career level."""

    level_code: str  # The standardized level code (L1-L6)
    track: str  # Career track (ENG, EM, PM, SALES, DESIGN)
    confidence: float  # Confidence score between 0 and 1


def determine_career_level_llm(
    title: str, company: str, total_months: int
) -> tuple[str, str]:
    """
    Use LLM to determine the career level and track based on the job title and company.

    Args:
        title: The job title to analyze
        company: The company name
        total_months: The total months of experience
    Returns:
        tuple[str, str]: Tuple of (level code, track code)
    """
    prompt = f"""Analyze the job title '{title}' at company '{company}' and classify it into one of these career tracks and levels:

    {LEVEL_TITLES}

    Return the most appropriate track code (ENG/EM/PM/SALES/DESIGN) and level (L1-L6).
    Keep in mind the total months of experience this person has worked {total_months}.
    Consider company context and years of experience implied by the title.
"""
    structured_llm = llm_fast.with_structured_output(CareerLevelAnalysis)
    result = structured_llm.invoke(prompt)

    if result.confidence < 0.7:
        # Fall back to heuristic matching for low confidence results
        return determine_level_heuristic(title)

    return result.level_code, result.track


def determine_level_heuristic(title: str) -> tuple[str, str]:
    """Fallback method using simple pattern matching for level determination."""
    title_lower = title.lower()

    # Check each track and its levels
    for track, levels in LEVEL_TITLES.items():
        for level, patterns in levels.items():
            if any(pattern in title_lower for pattern in patterns):
                return level, track

    # Default fallbacks based on common terms
    if any(term in title_lower for term in ["senior", "sr.", "sr ", "lead"]):
        # Determine track for senior role
        if "engineer" in title_lower:
            return "L3", "ENG"
        elif "product" in title_lower:
            return "L3", "PM"
        elif "sales" in title_lower:
            return "L3", "SALES"
        elif "design" in title_lower:
            return "L3", "DESIGN"
    elif any(
        term in title_lower for term in ["junior", "jr.", "jr ", "associate", "entry"]
    ):
        # Determine track for junior role
        if "engineer" in title_lower:
            return "L1", "ENG"
        elif "product" in title_lower:
            return "L1", "PM"
        elif "sales" in title_lower:
            return "L1", "SALES"
        elif "design" in title_lower:
            return "L1", "DESIGN"

    # Default to L2 Engineering if no clear match
    return "L2", "ENG"
