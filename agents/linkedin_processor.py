import re
from models.linkedin import LinkedInProfile, LinkedInCompany
from services.proxycurl import get_linkedin_profile, get_company
from services.firestore import db
import asyncio
import logging


async def get_experience_companies(profile: LinkedInProfile) -> None:
    """
    Get and store company data for all experiences in a profile.
    If company exists in Firebase, use cached data.
    If not, fetch from ProxyCurl and store in Firebase.
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

    # Fetch all uncached companies concurrently
    if tasks:
        company_results = await asyncio.gather(
            *[get_company(exp.company_linkedin_profile_url) for exp, _, _ in tasks]
        )

        # Update experiences and store in Firebase
        for (exp, _, company_ref), company in zip(tasks, company_results):
            if company:
                company_dict = company.dict()
                company_ref.set(company_dict)
                exp.company_data = company


async def get_linkedin_profile_with_companies(
    url: str,
) -> tuple[str, LinkedInProfile, str]:
    try:
        # First get the basic profile
        full_name, profile, public_id = await get_linkedin_profile(url)

        if not full_name or not profile or not public_id:
            raise ValueError("Missing required profile data from LinkedIn API")

        # Get and store company data for experiences
        await get_experience_companies(profile)

        # Analyze career metrics
        profile.analyze_career()

        # Save profile to Firebase - company_data will be automatically excluded
        profile_dict = profile.dict()
        profile_ref = db.collection("candidates").document(public_id)
        profile_ref.set(profile_dict, merge=True)

        return full_name, profile, public_id
    except Exception as e:
        logging.error(f"Failed to get LinkedIn profile for URL {url}: {str(e)}")
        raise
