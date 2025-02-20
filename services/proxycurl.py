import requests
from models.linkedin import (
    LinkedInProfile,
    LinkedInExperience,
    LinkedInEducation,
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
