import requests
from models.linkedin import (
    LinkedInProfile,
    LinkedInExperience,
    LinkedInEducation,
    LinkedInCompany,
    CompanyLocation,
    Investor,
    Funding,
)
from services.get_secret import get_secret
from services.firestore import db
from datetime import datetime


def get_linkedin_profile(url: str) -> tuple[str, LinkedInProfile, str] | None:
    """
    Get LinkedIn profile data from Crustdata API.

    Args:
        url: LinkedIn profile URL

    Returns:
        tuple[str, LinkedInProfile, str] | None: Tuple of (full name, profile object, public identifier) or None if screening fails
    """
    headers = {"Authorization": f"Token {get_secret('crustdata-api-key', '1')}"}
    api_endpoint = "https://api.crustdata.com/screener/person/enrich"

    # First try without real-time enrichment
    params = {
        "linkedin_profile_url": url,
        "enrich_realtime": False,
    }

    try:
        response = requests.get(api_endpoint, params=params, headers=headers)
        data = response.json()

        # If no data found, retry with real-time enrichment
        if (
            response.status_code != 200
            or not data
            or not data[0]
            or (isinstance(data[0], dict) and "error" in data[0])
        ):
            params["enrich_realtime"] = True
            response = requests.get(api_endpoint, params=params, headers=headers)
            if response.status_code != 200 or not data or not data[0]:
                return None

        profile_data = data[0]

        # Convert experiences
        experiences = []
        all_employers = profile_data.get("current_employers", []) + profile_data.get(
            "past_employers", []
        )
        for emp in all_employers:
            exp = LinkedInExperience(
                title=emp.get("employee_title"),
                company=emp.get("employer_name"),
                description=emp.get("employee_description"),
                starts_at=(
                    datetime.fromisoformat(emp.get("start_date")).date()
                    if emp.get("start_date")
                    else None
                ),
                ends_at=(
                    datetime.fromisoformat(emp.get("end_date")).date()
                    if emp.get("end_date")
                    else None
                ),
                location=emp.get("employee_location"),
                company_linkedin_profile_url=f"linkedin.com/company/{emp.get('employer_linkedin_id')}",
            )
            experiences.append(exp)

        # Convert education
        education = []
        for edu in profile_data.get("education_background", []):
            education_entry = LinkedInEducation(
                school=edu.get("institute_name"),
                degree_name=edu.get("degree_name"),
                field_of_study=edu.get("field_of_study"),
                starts_at=(
                    datetime.fromisoformat(edu.get("start_date")).date()
                    if edu.get("start_date")
                    else None
                ),
                ends_at=(
                    datetime.fromisoformat(edu.get("end_date")).date()
                    if edu.get("end_date")
                    else None
                ),
                school_linkedin_profile_url=edu.get("institute_linkedin_url"),
                logo_url=edu.get("institute_logo_url"),
            )
            education.append(education_entry)

        # Convert the raw response into our structured model
        profile = LinkedInProfile(
            full_name=profile_data.get("name"),
            occupation=profile_data.get("title"),
            headline=profile_data.get("headline"),
            summary=profile_data.get("summary"),
            city=profile_data.get("location", "").split(",")[0].strip()
            if profile_data.get("location")
            else None,
            country=profile_data.get("location", "").split(",")[-1].strip()
            if profile_data.get("location")
            else None,
            public_identifier=url.split("/in/")[-1].split("/")[0]
            if "/in/" in url
            else None,
            experiences=experiences,
            education=education,
        )

        return profile.full_name, profile, profile.public_identifier
    except Exception as e:
        print(e)
        return None


def get_linkedin_profiles(urls: list[str]) -> list[tuple[str, LinkedInProfile, str]]:
    """
    Get multiple LinkedIn profiles in a single batch request.

    Args:
        urls: List of LinkedIn profile URLs (max 25)

    Returns:
        List[Tuple[str, LinkedInProfile, str]]: List of (full name, profile object, public identifier) tuples
    """
    if len(urls) > 25:
        raise ValueError("Maximum of 25 URLs allowed per batch request")

    results = []
    for url in urls:
        profile_result = get_linkedin_profile(url)
        if profile_result:
            results.append(profile_result)

    return results


def get_company(linkedin_company_url: str) -> LinkedInCompany | None:
    """
    Get comprehensive company profile data from LinkedIn using Crustdata API.
    First identifies the company, then gets detailed information.

    Args:
        linkedin_company_url (str): URL of the LinkedIn company profile

    Returns:
        LinkedInCompany | None: Structured company profile data or None if screening fails
    """
    try:
        api_key = get_secret("crustdata-api-key", "1")
        headers = {
            "Authorization": f"Token {api_key}",
            "Accept": "application/json",
        }

        # First identify the company
        identify_endpoint = "https://api.crustdata.com/screener/identify/"
        identify_data = {"query_company_linkedin_url": linkedin_company_url, "count": 1}

        identify_response = requests.post(
            identify_endpoint, json=identify_data, headers=headers
        )
        if identify_response.status_code != 200:
            return None

        identify_data = identify_response.json()
        if not identify_data or len(identify_data) == 0:
            return None

        company_data = identify_data[0]
        linkedin_url = company_data.get("linkedin_profile_url")

        if not linkedin_url:
            return None

        # Check if company exists in Firebase
        company_id = linkedin_url.split("/company/")[-1].split("/")[0]
        company_ref = db.collection("companies").document(company_id)
        company_doc = company_ref.get()

        if company_doc.exists:
            return LinkedInCompany(**company_doc.to_dict())

        # Get detailed company data from Crustdata
        company_endpoint = "https://api.crustdata.com/screener/company"
        params = {
            "company_linkedin_url": linkedin_url,
        }

        response = requests.get(company_endpoint, params=params, headers=headers)
        if response.status_code != 200:
            return None

        data = response.json()
        if not data or len(data) == 0:
            return None

        company_data = data[0]

        # Construct funding data if available
        funding_data = None
        if company_data.get("funding_and_investment"):
            funding_info = company_data["funding_and_investment"]
            if funding_info.get("funding_milestones_timeseries"):
                funding_data = []
                for milestone in funding_info["funding_milestones_timeseries"]:
                    # Create investor list for this funding round
                    investors = []
                    if milestone.get("funding_milestone_investors"):
                        for inv in milestone["funding_milestone_investors"].split(","):
                            investors.append(
                                Investor(
                                    name=inv.strip(),
                                    type=None,  # Not provided in milestone data
                                    linkedin_profile_url=None,  # Not provided in milestone data
                                )
                            )

                    funding = Funding(
                        funding_type=milestone.get("funding_round"),
                        money_raised=milestone.get("funding_milestone_amount_usd"),
                        announced_date={
                            "day": datetime.fromisoformat(milestone.get("date")).day,
                            "month": datetime.fromisoformat(
                                milestone.get("date")
                            ).month,
                            "year": datetime.fromisoformat(milestone.get("date")).year,
                        },
                        number_of_investors=len(investors) if investors else None,
                        investor_list=investors,
                    )
                    funding_data.append(funding)

        # Convert to our LinkedInCompany model
        company = LinkedInCompany(
            company_name=company_data.get("company_name", ""),
            description=company_data.get("linkedin_company_description"),
            website=company_data.get("company_website"),
            industry=company_data.get("industry"),
            company_size=[company_data.get("headcount", {}).get("linkedin_headcount")]
            if company_data.get("headcount")
            else None,
            company_size_on_linkedin=company_data.get("headcount", {}).get(
                "linkedin_headcount"
            ),
            company_type=company_data.get("company_type"),
            founded_year=int(company_data.get("year_founded")[:4])
            if company_data.get("year_founded")
            else None,
            specialties=company_data.get("taxonomy", {}).get(
                "linkedin_specialities", []
            )
            or [],
            locations=[
                CompanyLocation(
                    city=company_data.get("headquarters", "").split(",")[0].strip()
                    if company_data.get("headquarters")
                    else None,
                    country=company_data.get("hq_country"),
                    is_hq=True,
                    line_1=company_data.get("hq_street_address"),
                )
            ]
            if company_data.get("headquarters") or company_data.get("hq_country")
            else [],
            hq=CompanyLocation(
                city=company_data.get("headquarters", "").split(",")[0].strip()
                if company_data.get("headquarters")
                else None,
                country=company_data.get("hq_country"),
                is_hq=True,
                line_1=company_data.get("hq_street_address"),
            )
            if company_data.get("headquarters") or company_data.get("hq_country")
            else None,
            follower_count=company_data.get("linkedin_followers", {}).get(
                "linkedin_followers"
            ),
            profile_pic_url=company_data.get("linkedin_logo_url"),
            background_cover_image_url=None,  # Not provided by Crustdata
            tagline=None,  # Not provided by Crustdata
            universal_name_id=None,  # Not provided by Crustdata
            linkedin_internal_id=company_data.get("linkedin_id"),
            search_id=None,  # Not provided by Crustdata
            updates=[],  # Not provided by Crustdata
            similar_companies=[],  # Not provided by Crustdata
            affiliated_companies=[],  # Not provided by Crustdata
            funding_data=funding_data,
        )

        # Store in Firebase
        company_ref.set(company.dict())

        return company
    except Exception as e:
        print(e)
        return None
