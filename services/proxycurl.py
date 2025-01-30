import requests
import asyncio
import aiohttp
from datamodels.linkedin import (
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
from datetime import date
from services.get_secret import get_secret
from typing import Dict, Optional
from services.firestore import db
from google.cloud.firestore import DocumentReference


def convert_date_dict(date_dict: dict) -> date:
    """Convert a date dictionary from Proxycurl API to a Python date object."""
    if not date_dict or not all(k in date_dict for k in ["year", "month", "day"]):
        return None
    return date(year=date_dict["year"], month=date_dict["month"], day=date_dict["day"])


def get_linkedin_profile_with_companies(
    url: str,
) -> tuple[str, LinkedInProfile, str]:
    """
    Get LinkedIn profile data with enriched company information for experiences.

    Args:
        url: LinkedIn profile URL

    Returns:
        tuple[str, LinkedInProfile, str]: Tuple of (full name, profile object, public identifier)
    """
    # First get the basic profile
    full_name, profile, public_id = get_linkedin_profile(url)

    # Then fetch company data asynchronously and save to Firebase
    company_data = get_experience_companies(profile)

    # Enrich the profile with company data and references
    enrich_profile_with_company_refs(profile, company_data)

    # Save the enriched profile to Firebase with company references
    profile_dict = profile.dict()

    # Convert experiences to include company references
    profile_dict["experiences"] = [
        {
            **exp.dict(
                exclude={"company_data"}
            ),  # Exclude company_data to avoid duplication
            "company_ref": exp.company_ref if exp.company_ref else None,
        }
        for exp in profile.experiences
    ]

    # Save to Firebase
    profile_ref = db.collection("candidates").document(public_id)
    profile_ref.set(profile_dict, merge=True)

    return full_name, profile, public_id


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
                company=exp["company"] if "company" in exp else "No Company",
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


def get_company_ref(company_url: str) -> DocumentReference:
    """
    Get a reference to a company document in Firestore.
    Converts LinkedIn company URL to a valid document ID.
    """
    # Extract company identifier from URL
    # Handle both formats: /company/name and /showcase/name
    company_id = company_url.rstrip("/")
    for prefix in ["/company/", "/showcase/"]:
        if prefix in company_id:
            company_id = company_id.split(prefix)[-1]
            break

    # Remove any remaining URL components or query parameters
    company_id = company_id.split("?")[0].split("#")[0]

    # Clean the ID to ensure it's valid for Firestore
    company_id = company_id.replace("/", "-").replace(".", "-").lower()

    if not company_id:
        raise ValueError(f"Could not extract valid company ID from URL: {company_url}")

    return db.collection("companies").document(company_id)


async def save_company_to_firebase(
    company: LinkedInCompany, company_url: str
) -> DocumentReference:
    """
    Save company data to Firebase if it doesn't exist or needs updating.

    Args:
        company: LinkedInCompany object
        company_url: LinkedIn company URL

    Returns:
        DocumentReference: Reference to the company document
    """
    company_ref = get_company_ref(company_url)
    company_dict = company.dict()

    # Convert nested models to dicts
    if company_dict.get("locations"):
        company_dict["locations"] = [loc.dict() for loc in company.locations]
    if company_dict.get("hq"):
        company_dict["hq"] = company.hq.dict()
    if company_dict.get("updates"):
        company_dict["updates"] = [update.dict() for update in company.updates]
    if company_dict.get("similar_companies"):
        company_dict["similar_companies"] = [
            comp.dict() for comp in company.similar_companies
        ]
    if company_dict.get("affiliated_companies"):
        company_dict["affiliated_companies"] = [
            comp.dict() for comp in company.affiliated_companies
        ]
    if company_dict.get("funding_data"):
        company_dict["funding_data"] = [
            {
                **round.dict(),
                "investor_list": [inv.dict() for inv in round.investor_list],
            }
            for round in company.funding_data
        ]

    # Add metadata
    company_dict["linkedin_url"] = company_url
    company_dict["last_updated"] = date.today().isoformat()

    # Save to Firebase
    company_ref.set(company_dict, merge=True)
    return company_ref


async def get_company_async(
    session: aiohttp.ClientSession, linkedin_company_url: str
) -> Optional[tuple[LinkedInCompany, DocumentReference]]:
    """
    Async version of get_company function that fetches company data and saves to Firebase.

    Args:
        session: aiohttp ClientSession for making requests
        linkedin_company_url: URL of the LinkedIn company profile

    Returns:
        Optional[tuple[LinkedInCompany, DocumentReference]]: Company data and Firebase reference
    """
    try:
        # Check if we have recent data in Firebase
        company_ref = get_company_ref(linkedin_company_url)
        company_doc = company_ref.get()

        if company_doc.exists:
            company_data = company_doc.to_dict()
            # Check if data is recent (within last 30 days)
            last_updated = date.fromisoformat(
                company_data.get("last_updated", "2000-01-01")
            )
            if (date.today() - last_updated).days < 180:
                # Convert stored data back to LinkedInCompany
                return LinkedInCompany(**company_data), company_ref

        # If no recent data, fetch from API
        api_key = get_secret("proxycurl-api-key", "1")
        headers = {"Authorization": "Bearer " + api_key}
        api_endpoint = "https://nubela.co/proxycurl/api/linkedin/company"
        params = {
            "url": linkedin_company_url,
            "resolve_numeric_id": "true",
            "categories": "exclude",
            "funding_data": "include",
            "extra": "exclude",
            "exit_data": "exclude",
            "acquisitions": "exclude",
            "use_cache": "if-present",
        }

        async with session.get(
            api_endpoint, params=params, headers=headers
        ) as response:
            data = await response.json()

            # Convert API response to LinkedInCompany (existing conversion code)
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
                locations=[CompanyLocation(**loc) for loc in data.get("locations", [])],
                hq=CompanyLocation(**data["hq"]) if data.get("hq") else None,
                follower_count=data.get("follower_count"),
                profile_pic_url=data.get("profile_pic_url"),
                background_cover_image_url=data.get("background_cover_image_url"),
                tagline=data.get("tagline"),
                universal_name_id=data.get("universal_name_id"),
                linkedin_internal_id=data.get("linkedin_internal_id"),
                search_id=data.get("search_id"),
                updates=[CompanyUpdate(**update) for update in data.get("updates", [])],
                similar_companies=[
                    AffiliatedCompany(**comp)
                    for comp in data.get("similar_companies", [])
                ],
                affiliated_companies=[
                    AffiliatedCompany(**comp)
                    for comp in data.get("affiliated_companies", [])
                ],
                funding_data=[
                    Funding(
                        **{
                            **round,
                            "investor_list": [
                                Investor(**inv)
                                for inv in round.get("investor_list", [])
                            ],
                        }
                    )
                    for round in data.get("funding_data", [])
                ]
                if data.get("funding_data")
                else None,
            )

            # Save to Firebase
            company_ref = await save_company_to_firebase(company, linkedin_company_url)
            return company, company_ref

    except Exception as e:
        print(f"Error fetching company data for {linkedin_company_url}: {str(e)}")
        return None


def get_experience_companies(
    profile: LinkedInProfile,
) -> Dict[str, tuple[LinkedInCompany, DocumentReference]]:
    """
    Fetch company data for all experiences and save to Firebase.
    Skips school URLs to avoid processing educational institutions as companies.

    Args:
        profile: LinkedInProfile object containing experiences

    Returns:
        Dict[str, tuple[LinkedInCompany, DocumentReference]]: URLs to company data and refs
    """
    company_data = {}

    # Collect unique company URLs from experiences, excluding school URLs
    company_urls = {
        exp.company_linkedin_profile_url
        for exp in profile.experiences
        if exp.company_linkedin_profile_url
        and "/school/" not in exp.company_linkedin_profile_url.lower()
    }

    if not company_urls:
        return company_data

    # Process each company URL synchronously
    for url in company_urls:
        try:
            # Check if we have recent data in Firebase
            company_ref = get_company_ref(url)
            company_doc = company_ref.get()

            if company_doc.exists:
                company_data_dict = company_doc.to_dict()
                # Check if data is recent (within last 180 days)
                last_updated = date.fromisoformat(
                    company_data_dict.get("last_updated", "2000-01-01")
                )
                if (date.today() - last_updated).days < 180:
                    # Use cached data
                    company = LinkedInCompany(**company_data_dict)
                    company_data[url] = (company, company_ref)
                    continue

            # If no recent data, fetch from API
            company = get_company(url)
            if company:
                # Save to Firebase
                company_dict = company.dict()
                company_dict["linkedin_url"] = url
                company_dict["last_updated"] = date.today().isoformat()
                company_ref.set(company_dict, merge=True)
                company_data[url] = (company, company_ref)

        except Exception as e:
            print(f"Error processing company {url}: {str(e)}")
            continue

    return company_data


def enrich_profile_with_company_refs(
    profile: LinkedInProfile,
    company_data: Dict[str, tuple[LinkedInCompany, DocumentReference]],
) -> None:
    """
    Enrich profile experiences with company data and references.

    Args:
        profile: LinkedInProfile to enrich
        company_data: Dictionary of company data and references
    """
    for experience in profile.experiences:
        if experience.company_linkedin_profile_url in company_data:
            company, ref = company_data[experience.company_linkedin_profile_url]
            experience.company_data = company
            # Store the reference path for Firebase
            experience.company_ref = ref.path
