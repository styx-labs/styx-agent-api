from typing import Dict
from google.cloud.firestore import DocumentReference
from datamodels.linkedin import (
    LinkedInProfile,
    LinkedInCompany,
)
from services.proxycurl import get_linkedin_profile, get_company
from services.firestore import db
from agents.career_analyzer import analyze_career


def get_linkedin_profile_with_companies(url: str) -> tuple[str, LinkedInProfile, str]:
    """
    Get LinkedIn profile data and enrich with company data.
    Companies are fetched from Firebase if available, otherwise from ProxyCurl.
    Company data is stored separately in Firebase and not included in the profile storage.

    Args:
        url: LinkedIn profile URL

    Returns:
        tuple[str, LinkedInProfile, str]: Tuple of (full name, profile object, public identifier)
    """
    # First get the basic profile
    full_name, profile, public_id = get_linkedin_profile(url)

    # For each company in experiences, get or fetch company data
    for exp in profile.experiences:
        if (
            exp.company_linkedin_profile_url
            and "school" not in exp.company_linkedin_profile_url
        ):
            company_id = exp.company_linkedin_profile_url.split("/")[-1]
            if company_id:
                company_ref = db.collection("companies").document(company_id)
                company_doc = company_ref.get()

                if company_doc.exists:
                    # Use cached company data
                    company_data = company_doc.to_dict()
                    exp.company_data = LinkedInCompany(**company_data)
                else:
                    # Fetch and store new company data
                    company = get_company(exp.company_linkedin_profile_url)
                    company_dict = company.dict()
                    company_ref.set(company_dict)
                    exp.company_data = company

    # Analyze career metrics
    profile.analyze_career()

    # Save profile to Firebase - company_data will be automatically excluded
    profile_dict = profile.dict()
    profile_ref = db.collection("candidates").document(public_id)
    profile_ref.set(profile_dict, merge=True)

    return full_name, profile, public_id


def store_experience_companies(profile: LinkedInProfile) -> None:
    """
    Fetch and store company data for all experiences in a profile.
    Each company is stored in Firebase with its LinkedIn URL as the ID.
    """
    for exp in profile.experiences:
        if exp.company_linkedin_profile_url:
            # Get company data
            company = get_company(exp.company_linkedin_profile_url)

            # Store in Firebase
            company_dict = company.dict()
            company_id = exp.company_linkedin_profile_url.split("/")[-1]
            db.collection("companies").document(company_id).set(
                company_dict, merge=True
            )


async def save_company_to_firebase(
    company: LinkedInCompany, company_url: str
) -> DocumentReference:
    """Save company data to Firebase and return the document reference."""
    company_dict = company.dict()
    company_ref = db.collection("companies").document(company_url.split("/")[-1])
    await company_ref.set(company_dict, merge=True)
    return company_ref


def get_experience_companies(
    profile: LinkedInProfile,
) -> Dict[str, tuple[LinkedInCompany, DocumentReference]]:
    """
    Get company data for all experiences in a profile.
    Returns a dictionary mapping company URLs to tuples of (company data, Firebase reference).
    """
    company_data = {}
    for exp in profile.experiences:
        if exp.company_linkedin_profile_url:
            company_data[exp.company_linkedin_profile_url] = get_company(
                exp.company_linkedin_profile_url
            )

    return company_data


def enrich_profile_with_company_refs(
    profile: LinkedInProfile,
    company_data: Dict[str, tuple[LinkedInCompany, DocumentReference]],
) -> None:
    """Enrich profile experiences with company data and Firebase references."""
    for exp in profile.experiences:
        if exp.company_linkedin_profile_url in company_data:
            company, ref = company_data[exp.company_linkedin_profile_url]
            exp.company_data = company
            exp.company_ref = ref
