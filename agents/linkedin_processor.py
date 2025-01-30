import re
from datamodels.linkedin import LinkedInProfile, LinkedInCompany
from services.proxycurl import get_linkedin_profile, get_company
from services.firestore import db


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

    # Get and store company data for experiences
    get_experience_companies(profile)

    # Analyze career metrics
    profile.analyze_career()

    # Save profile to Firebase - company_data will be automatically excluded
    profile_dict = profile.dict()
    profile_ref = db.collection("candidates").document(public_id)
    profile_ref.set(profile_dict, merge=True)

    return full_name, profile, public_id


def get_experience_companies(profile: LinkedInProfile) -> None:
    """
    Get and store company data for all experiences in a profile.
    If company exists in Firebase, use cached data.
    If not, fetch from ProxyCurl and store in Firebase.
    Attaches company data to each experience in the profile.
    """
    for exp in profile.experiences:
        if (
            exp.company_linkedin_profile_url
            and "school" not in exp.company_linkedin_profile_url
        ):
            # Extract company ID from URL using regex
            match = re.search(
                r"linkedin\.com/company/([^/?]+)", exp.company_linkedin_profile_url
            )
            company_id = match.group(1) if match else None

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
