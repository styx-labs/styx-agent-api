import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from services.firestore import (
    get_cached_candidate,
    check_cached_candidate_exists,
    create_candidate,
    db,
)
from models.linkedin import LinkedInProfile


def update_all_candidates():
    try:
        # Fetch all candidate IDs from Firestore
        candidate_ids = [doc.id for doc in db.collection("candidates").stream()]

        for candidate_id in candidate_ids:
            # Check if the candidate exists and fetch their data
            if check_cached_candidate_exists(candidate_id):
                candidate = get_cached_candidate(candidate_id)

                # Convert candidate profile to LinkedInProfile object
                profile = LinkedInProfile(**candidate["profile"])

                # Analyze career metrics
                profile.analyze_career()

                candidate["profile"] = profile.dict()

                # Update candidate in Firestore
                create_candidate(candidate)

        logging.info("All candidates updated successfully.")
    except Exception as e:
        logging.error(f"Error updating candidates: {str(e)}")


if __name__ == "__main__":
    update_all_candidates()
