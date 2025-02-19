import re
from models.linkedin import LinkedInProfile, LinkedInCompany
from services.crustdata import get_linkedin_profile, get_company
from services.firestore import db
import logging
import services.firestore as firestore
from utils.linkedin_utils import extract_linkedin_id


def get_experience_companies(profile: LinkedInProfile) -> None:
    """
    Get and store company data for all experiences in a profile.
    If company exists in Firebase, use cached data.
    If not, fetch from Crustdata and store in Firebase.
    Attaches company data to each experience in the profile.
    """
    tasks = []
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
                    # Add to list of companies to fetch
                    tasks.append((exp, company_id, company_ref))

                    company = get_company(exp.company_linkedin_profile_url)
                    if company:
                        company_dict = company.dict()
                        company_ref.set(company_dict)
                        exp.company_data = company
                    else:
                        exp.company_data = None


def get_linkedin_profile_with_companies(
    url: str,
) -> tuple[str, LinkedInProfile, str]:
    try:
        public_id = extract_linkedin_id(url)
        # Check if the candidate is already in Firebase
        if firestore.check_cached_candidate_exists(public_id):
            cached_candidate = firestore.get_cached_candidate(public_id)
            full_name = cached_candidate["name"]
            profile = LinkedInProfile(**cached_candidate["profile"])
        else:
            # First get the basic profile
            full_name, profile, public_id = get_linkedin_profile(url)

        # Get and store company data for experiences
        get_experience_companies(profile)

        profile.analyze_career()

        # Save profile to Firebase - company_data will be automatically excluded
        profile_dict = profile.dict()
        profile_ref = db.collection("candidates").document(public_id)
        profile_ref.set(profile_dict, merge=True)

        return full_name, profile, public_id
    except Exception as e:
        logging.error(f"Failed to get LinkedIn profile for URL {url}: {str(e)}")
        raise
