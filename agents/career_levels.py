"""
Career level definitions and track-specific salary ranges.
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
            "sales associate",
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

# Base salary ranges by track and level (35th, 50th, 65th percentile)
SALARY_RANGES = {
    # Software Engineering (Base reference)
    "ENG": {
        "L1": (127000, 153362, 170000),
        "L2": (188000, 215675, 257727),
        "L3": (247993, 303307, 356535),
        "L4": (310000, 426546, 527340),
        "L5": (382050, 599859, 701821),
    },
    # Engineering Management (15-20% higher than IC)
    "EM": {
        "L1": (146050, 176366, 195500),  # 15% higher than ENG
        "L2": (216200, 247926, 296386),
        "L3": (285192, 348803, 410015),
        "L4": (356500, 490528, 606441),
        "L5": (439358, 689838, 807094),
        "L6": (521500, 750000, 900000),  # Executive level
    },
    # Product Management (90-95% of engineering)
    "PM": {
        "L1": (120650, 145694, 161500),  # 95% of ENG
        "L2": (178600, 204891, 244841),
        "L3": (235593, 288142, 338708),
        "L4": (294500, 405219, 500973),
        "L5": (362948, 569866, 666730),
        "L6": (439358, 689838, 807094),  # Director/VP level
    },
    # Sales (Base at 70%, OTE at 140% of engineering)
    "SALES": {
        # Format: (Base_35th, Base_50th, OTE_65th)
        "L1": (88900, 107353, 238000),  # SDR/BDR
        "L2": (131600, 150973, 360818),  # AE
        "L3": (173595, 212315, 499149),  # Senior AE
        "L4": (217000, 298582, 738276),  # Regional Manager
        "L5": (267435, 419901, 982549),  # Director
        "L6": (350000, 500000, 1200000),  # VP/CRO
    },
    # Design (85-90% of engineering)
    "DESIGN": {
        "L1": (114300, 138026, 153000),  # 90% of ENG
        "L2": (169200, 194108, 231954),
        "L3": (223194, 272976, 320882),
        "L4": (279000, 383891, 474606),
        "L5": (343845, 539873, 631639),
        "L6": (401143, 599859, 701821),  # Design leadership
    },
}

# Location tiers and their multipliers
LOCATION_TIERS = {
    # US Tiers
    "us_tier_1": {  # Major US tech hubs
        "multiplier": 1.2,
        "cities": ["san francisco", "new york", "seattle"],
        "description": "Major US tech hubs with highest compensation",
    },
    "us_tier_2": {  # Secondary US tech hubs
        "multiplier": 1.1,
        "cities": ["boston", "los angeles", "chicago"],
        "description": "Secondary US tech hubs with strong tech presence",
    },
    "us_tier_3": {  # Other US major cities
        "multiplier": 1.0,
        "cities": ["austin", "denver", "portland", "atlanta"],
        "description": "Other major US cities with growing tech scenes",
    },
    # European Tiers
    "eu_tier_1": {  # Top European tech hubs
        "multiplier": 0.95,  # 95% of US base
        "cities": ["zurich", "london", "amsterdam"],
        "countries": ["switzerland", "uk", "netherlands"],
        "description": "Premium European tech hubs with highest EU compensation",
    },
    "eu_tier_2": {  # Strong European tech cities
        "multiplier": 0.8,  # 80% of US base
        "cities": ["berlin", "munich", "paris", "stockholm", "dublin"],
        "countries": ["germany", "france", "sweden", "ireland"],
        "description": "Major European cities with strong tech presence",
    },
    "eu_tier_3": {  # Other European tech cities
        "multiplier": 0.65,  # 65% of US base
        "cities": ["madrid", "barcelona", "lisbon", "warsaw", "prague"],
        "countries": ["spain", "portugal", "poland", "czech republic"],
        "description": "Growing European tech hubs with competitive local compensation",
    },
    # Remote
    "remote_us": {
        "multiplier": 0.9,  # 90% of US base
        "keywords": ["remote", "work from home", "wfh"],
        "description": "US-based remote work",
    },
    "remote_eu": {
        "multiplier": 0.7,  # 70% of US base
        "keywords": ["remote", "work from home", "wfh"],
        "description": "EU-based remote work",
    },
}

# Country-specific adjustments (multiplied on top of tier multiplier)
COUNTRY_ADJUSTMENTS = {
    "switzerland": 1.15,  # Swiss premium
    "uk": 1.05,  # UK premium
    "netherlands": 1.0,  # Base for EU Tier 1
    "germany": 0.95,  # Slight discount to EU Tier 1
    "ireland": 0.95,  # Dublin tech hub adjustment
    "france": 0.9,  # French market adjustment
    "sweden": 0.9,  # Nordic market adjustment
    "spain": 0.8,  # Southern European adjustment
    "portugal": 0.75,  # Growing tech hub
    "poland": 0.75,  # Eastern European hub
    "czech republic": 0.75,  # Eastern European hub
}

# Company type multipliers
COMPANY_TYPE_MULTIPLIERS = {
    "big_tech": 1.3,  # FAANG, Big Tech
    "unicorn": 1.2,  # Unicorn startups
    "growth": 1.1,  # Growth stage, well-funded
    "startup": 0.8,  # Early stage startups
    "standard": 1.0,  # Default for established companies
}


class CareerLevelAnalysis(SerializableModel):
    """Model for LLM analysis of career level."""

    level_code: str  # The standardized level code (L1-L6)
    track: str  # Career track (ENG, EM, PM, SALES, DESIGN)
    confidence: float  # Confidence score between 0 and 1


class LocationAnalysis(SerializableModel):
    """Model for LLM analysis of location tier."""

    tier: (
        str  # Location tier (us_tier_1, us_tier_2, etc. or eu_tier_1, eu_tier_2, etc.)
    )
    country: str  # Country name (for applying country-specific adjustments)
    confidence: float  # Confidence score between 0 and 1
    reasoning: str  # Brief explanation of the classification


class CompanyAnalysis(SerializableModel):
    """Model for LLM analysis of company type."""

    type: str  # Company type (big_tech, unicorn, growth, startup, standard)
    confidence: float  # Confidence score between 0 and 1
    reasoning: str  # Brief explanation of the classification


def determine_career_level_llm(title: str, company: str) -> tuple[str, str]:
    """
    Use LLM to determine the career level and track based on the job title and company.

    Args:
        title: The job title to analyze
        company: The company name

    Returns:
        tuple[str, str]: Tuple of (level code, track code)
    """
    prompt = f"""Analyze the job title '{title}' at company '{company}' and classify it into one of these career tracks and levels:

Engineering (ENG):
L1 - Entry Level (0-2 yrs): Junior/Associate Engineer
L2 - Mid Level (2-5 yrs): Software Engineer
L3 - Senior (5-8 yrs): Senior Engineer
L4 - Staff (8-12 yrs): Staff Engineer
L5 - Principal (12+ yrs): Principal Engineer
L6 - Distinguished: Fellow/Distinguished Engineer

Engineering Management (EM):
L1 - Team Lead
L2 - Engineering Manager
L3 - Senior Engineering Manager
L4 - Director of Engineering
L5 - Senior Director/VP
L6 - CTO/SVP Engineering

Product Management (PM):
L1 - APM/Junior PM
L2 - Product Manager
L3 - Senior PM
L4 - Group PM/Principal PM
L5 - Director of Product
L6 - VP Product/CPO

Sales:
L1 - SDR/BDR
L2 - Account Executive
L3 - Senior AE
L4 - Regional Manager
L5 - Director of Sales
L6 - VP Sales/CRO

Design:
L1 - Junior Designer
L2 - Product Designer
L3 - Senior Designer
L4 - Staff Designer
L5 - Principal/Director
L6 - VP Design/CDO

Return the most appropriate track code (ENG/EM/PM/SALES/DESIGN) and level (L1-L6).
Consider company context, years of experience implied by the title, and company prestige.
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


def determine_location_tier_llm(location: str) -> tuple[str, str]:
    """
    Use LLM to determine the location tier based on the location string.

    Args:
        location: Location string (city, state, country, or remote)

    Returns:
        tuple[str, str]: Tuple of (tier, country)
    """
    prompt = f"""Analyze the location '{location}' and classify it into one of these tiers:

US Tiers:
Tier 1 (Major US Tech Hubs):
- San Francisco Bay Area, Silicon Valley
- New York City, Manhattan
- Seattle
- Other US locations with extremely high tech concentration

Tier 2 (Secondary US Tech Hubs):
- Boston
- Los Angeles
- Chicago
- Austin
- Other major US cities with strong tech presence

Tier 3 (Other US Major Cities):
- Denver
- Portland
- Atlanta
- Other US cities with growing tech scenes

European Tiers:
EU Tier 1 (Premium European Tech Hubs):
- Zurich, Switzerland
- London, UK
- Amsterdam, Netherlands
- Other top European tech cities

EU Tier 2 (Major European Tech Cities):
- Berlin, Munich (Germany)
- Paris (France)
- Stockholm (Sweden)
- Dublin (Ireland)
- Other major European tech hubs

EU Tier 3 (Growing European Tech Hubs):
- Madrid, Barcelona (Spain)
- Lisbon (Portugal)
- Warsaw (Poland)
- Prague (Czech Republic)
- Other growing European tech cities

Remote:
- If US-based: classify as remote_us
- If EU-based: classify as remote_eu
- Must explicitly mention remote work

Consider:
- Cost of living
- Tech industry presence
- Local market compensation
- Regional economic factors

Return:
1. The most appropriate tier (us_tier_1, us_tier_2, us_tier_3, eu_tier_1, eu_tier_2, eu_tier_3, remote_us, remote_eu)
2. The country name (for European locations)
3. Your reasoning
"""
    structured_llm = llm_fast.with_structured_output(LocationAnalysis)
    result = structured_llm.invoke(prompt)

    if result.confidence < 0.7:
        # Default to us_tier_3 for low confidence US locations
        # or eu_tier_3 for low confidence European locations
        if any(country in location.lower() for country in COUNTRY_ADJUSTMENTS.keys()):
            return "eu_tier_3", result.country or "unknown"
        return "us_tier_3", "us"

    return result.tier, result.country


def get_location_multiplier(location_tier: str, country: str = None) -> float:
    """
    Get the location-based salary multiplier, including country-specific adjustments.

    Args:
        location_tier: Location tier from LLM analysis
        country: Country name (if applicable) for additional adjustments

    Returns:
        float: Final location multiplier
    """
    base_multiplier = LOCATION_TIERS.get(location_tier, {}).get("multiplier", 1.0)

    if country and country.lower() in COUNTRY_ADJUSTMENTS:
        return base_multiplier * COUNTRY_ADJUSTMENTS[country.lower()]

    return base_multiplier


def determine_company_type_llm(company: str, description: str = "") -> str:
    """
    Use LLM to determine the company type based on company name and optional description.

    Args:
        company: Company name
        description: Optional company description or additional context

    Returns:
        str: Company type (big_tech, unicorn, growth, startup, standard)
    """
    prompt = f"""Analyze the company '{company}' {f'({description})' if description else ''} and classify it into one of these types:

Big Tech:
- FAANG (Facebook/Meta, Apple, Amazon, Netflix, Google)
- Major established tech companies (Microsoft, Salesforce, etc.)
- Industry leaders with significant market presence

Unicorn:
- Private companies valued at $1B+
- Well-known high-growth tech companies
- Significant funding and market presence

Growth:
- Series C+ funded companies
- Established market presence
- Strong growth trajectory
- Well-funded but not yet unicorn status

Startup:
- Early stage (pre-seed to Series B)
- Small team size
- Limited market presence
- Innovation-focused

Standard:
- Traditional established companies
- Non-tech focused enterprises
- Default classification if unclear

Consider:
- Company size and age
- Industry position
- Funding status
- Market recognition

Return the most appropriate type and explain your reasoning.
"""
    structured_llm = llm_fast.with_structured_output(CompanyAnalysis)
    result = structured_llm.invoke(prompt)

    if result.confidence < 0.7:
        # Default to standard for low confidence results
        return "standard"

    return result.type
