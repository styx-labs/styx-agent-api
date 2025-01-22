import requests
from datamodels.linkedin import LinkedInProfile, LinkedInExperience, LinkedInEducation
from datetime import date
from services.get_secret import get_secret


def convert_date_dict(date_dict: dict) -> date:
    """Convert a date dictionary from Proxycurl API to a Python date object."""
    if not date_dict or not all(k in date_dict for k in ["year", "month", "day"]):
        return None
    return date(year=date_dict["year"], month=date_dict["month"], day=date_dict["day"])


def get_linkedin_profile(url):
    api_key = get_secret("proxycurl-api-key", "1")
    headers = {"Authorization": "Bearer " + api_key}
    api_endpoint = "https://nubela.co/proxycurl/api/v2/linkedin"
    params = {"linkedin_profile_url": url}
    response = requests.get(api_endpoint, params=params, headers=headers)
    data = response.json()

    # Convert the raw response into our structured model
    profile = LinkedInProfile(
        full_name=data["full_name"],
        occupation=data.get("occupation"),
        headline=data.get("headline"),
        summary=data.get("summary"),
        city=data.get("city"),
        country=data.get("country"),
        public_identifier=data["public_identifier"],
        experiences=[
            LinkedInExperience(
                title=exp["title"],
                company=exp["company"],
                description=exp.get("description"),
                starts_at=convert_date_dict(exp.get("starts_at")),
                ends_at=convert_date_dict(exp.get("ends_at")),
                location=exp.get("location"),
            )
            for exp in data.get("experiences", [])
            if "title" in exp and "company" in exp
        ],
        education=[
            LinkedInEducation(
                school=edu["school"],
                degree_name=edu["degree_name"],
                field_of_study=edu["field_of_study"],
                starts_at=convert_date_dict(edu.get("starts_at")),
                ends_at=convert_date_dict(edu.get("ends_at")),
            )
            for edu in data.get("education", [])
            if all(k in edu for k in ["school", "degree_name", "field_of_study"])
        ],
    )

    return profile.full_name, profile, profile.public_identifier


def get_email(linkedin_profile_url: str):
    api_key = get_secret("proxycurl-api-key", "1")
    headers = {"Authorization": "Bearer " + api_key}
    api_endpoint = "https://nubela.co/proxycurl/api/contact-api/personal-email"
    params = {
        "linkedin_profile_url": linkedin_profile_url,
        "page_size": 1,
    }
    response = requests.get(api_endpoint, params=params, headers=headers)
    response = response.json()
    return response["emails"][0]
