import requests
import aiohttp
from models.linkedin import (
    LinkedInProfile,
    LinkedInExperience,
    LinkedInEducation,
    LinkedInCompany,
    CompanyLocation,
    AffiliatedCompany,
    CompanyUpdate,
    Funding,
    Investor,
)
from services.get_secret import get_secret
from utils.date_utils import convert_date_dict


def get_linkedin_profile(url: str) -> tuple[str, LinkedInProfile, str]:
    """
    Get basic LinkedIn profile data without company information.

    Args:
        url: LinkedIn profile URL

    Returns:
        tuple[str, LinkedInProfile, str]: Tuple of (full name, profile object, public identifier)
    """
    api_key = get_secret("proxycurl-api-key", "1")
    headers = {"Authorization": "Bearer " + api_key}
    api_endpoint = "https://nubela.co/proxycurl/api/v2/linkedin"
    params = {"linkedin_profile_url": url}
    response = requests.get(api_endpoint, params=params, headers=headers)
    if response.status_code != 200:
        raise ValueError("Missing required profile data from LinkedIn API")

    data = response.json()

    # Convert the raw response into our structured model
    profile = LinkedInProfile(
        full_name=data.get("full_name"),
        occupation=data.get("occupation"),
        headline=data.get("headline"),
        summary=data.get("summary"),
        city=data.get("city"),
        country=data.get("country"),
        public_identifier=data.get("public_identifier"),
        experiences=[
            LinkedInExperience(
                title=exp.get("title"),
                company=exp.get("company") if "company" in exp else "No Company",
                description=exp.get("description"),
                starts_at=convert_date_dict(exp.get("starts_at")),
                ends_at=convert_date_dict(exp.get("ends_at")),
                location=exp.get("location"),
                company_linkedin_profile_url=exp.get("company_linkedin_profile_url"),
            )
            for exp in data.get("experiences", [])
            if "title" in exp and "company" in exp
        ],
        education=[
            LinkedInEducation(
                school=edu.get("school"),
                degree_name=edu.get("degree_name"),
                field_of_study=edu.get("field_of_study"),
                starts_at=convert_date_dict(edu.get("starts_at")),
                ends_at=convert_date_dict(edu.get("ends_at")),
                school_linkedin_profile_url=edu.get("school_linkedin_profile_url"),
                logo_url=edu.get("logo_url"),
            )
            for edu in data.get("education", [])
            if all(k in edu for k in ["school", "degree_name", "field_of_study"])
        ],
    )

    return profile.full_name, profile, profile.public_identifier


def get_email(linkedin_profile_url: str) -> str:
    """Get email address associated with a LinkedIn profile."""
    api_key = get_secret("proxycurl-api-key", "1")
    headers = {"Authorization": "Bearer " + api_key}
    api_endpoint = "https://nubela.co/proxycurl/api/contact-api/personal-email"
    params = {
        "linkedin_profile_url": linkedin_profile_url,
        "page_size": 1,
    }
    response = requests.get(api_endpoint, params=params, headers=headers)
    response = response.json()
    if not response["emails"]:
        return get_work_email(linkedin_profile_url)
    return response["emails"][0]


def get_work_email(linkedin_profile_url: str):
    api_key = get_secret("proxycurl-api-key", "1")
    headers = {"Authorization": "Bearer " + api_key}
    api_endpoint = "https://nubela.co/proxycurl/api/linkedin/profile/email"
    params = {
        "linkedin_profile_url": linkedin_profile_url,
        "page_size": 1,
    }
    response = requests.get(api_endpoint, params=params, headers=headers)
    response = response.json()
    return response["emails"][0]


def get_company(linkedin_company_url: str) -> LinkedInCompany:
    """
    Get comprehensive company profile data from LinkedIn using Proxycurl API.

    Args:
        linkedin_company_url (str): URL of the LinkedIn company profile

    Returns:
        LinkedInCompany: Structured company profile data
    """
    api_key = get_secret("proxycurl-api-key", "1")
    headers = {"Authorization": "Bearer " + api_key}
    api_endpoint = "https://nubela.co/proxycurl/api/linkedin/company"
    params = {
        "url": linkedin_company_url,
        "categories": "exclude",
        "funding_data": "include",
        "extra": "exclude",
        "exit_data": "exclude",
        "acquisitions": "exclude",
        "use_cache": "if-present",
    }
    response = requests.get(api_endpoint, params=params, headers=headers)
    data = response.json()

    # Convert locations to CompanyLocation objects
    locations = [
        CompanyLocation(
            city=loc.get("city"),
            country=loc.get("country"),
            is_hq=loc.get("is_hq", False),
            line_1=loc.get("line_1"),
            postal_code=loc.get("postal_code"),
            state=loc.get("state"),
        )
        for loc in data.get("locations", [])
    ]

    # Convert HQ data if present
    hq = None
    if data.get("hq"):
        hq = CompanyLocation(
            city=data["hq"].get("city"),
            country=data["hq"].get("country"),
            is_hq=True,
            line_1=data["hq"].get("line_1"),
            postal_code=data["hq"].get("postal_code"),
            state=data["hq"].get("state"),
        )

    # Convert affiliated companies
    affiliated_companies = [
        AffiliatedCompany(
            industry=comp.get("industry"),
            link=comp["link"],
            location=comp.get("location"),
            name=comp["name"],
        )
        for comp in data.get("affiliated_companies", [])
    ]

    # Convert similar companies
    similar_companies = [
        AffiliatedCompany(
            industry=comp.get("industry"),
            link=comp["link"],
            location=comp.get("location"),
            name=comp["name"],
        )
        for comp in data.get("similar_companies", [])
    ]

    # Convert updates
    updates = [
        CompanyUpdate(
            article_link=update.get("article_link"),
            image=update.get("image"),
            posted_on=update.get("posted_on"),
            text=update.get("text"),
            total_likes=update.get("total_likes"),
        )
        for update in data.get("updates", [])
    ]

    # Convert funding data if present
    funding_data = None
    if data.get("funding_data"):
        funding_data = [
            Funding(
                funding_type=round.get("funding_type"),
                money_raised=round.get("money_raised"),
                announced_date=round.get("announced_date"),
                number_of_investors=round.get("number_of_investors"),
                investor_list=[
                    Investor(
                        linkedin_profile_url=inv.get("linkedin_profile_url"),
                        name=inv["name"],
                        type=inv.get("type"),
                    )
                    for inv in round.get("investor_list", [])
                ],
            )
            for round in data["funding_data"]
        ]

    # Convert the raw response into our structured model
    company = LinkedInCompany(
        company_name=data.get("name", ""),
        description=data.get("description"),
        website=data.get("website"),
        industry=data.get("industry"),
        company_size=data.get("company_size"),
        company_size_on_linkedin=data.get("company_size_on_linkedin"),
        company_type=data.get("company_type"),
        founded_year=data.get("founded_year"),
        specialties=data.get("specialities", []),
        locations=locations,
        hq=hq,
        follower_count=data.get("follower_count"),
        profile_pic_url=data.get("profile_pic_url"),
        background_cover_image_url=data.get("background_cover_image_url"),
        tagline=data.get("tagline"),
        universal_name_id=data.get("universal_name_id"),
        linkedin_internal_id=data.get("linkedin_internal_id"),
        search_id=data.get("search_id"),
        updates=updates,
        similar_companies=similar_companies,
        affiliated_companies=affiliated_companies,
        funding_data=funding_data,
    )

    return company
