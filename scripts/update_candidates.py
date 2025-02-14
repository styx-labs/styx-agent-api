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
from concurrent.futures import ThreadPoolExecutor, as_completed


def process_candidate(candidate_id):
    """Process a single candidate."""
    try:
        if check_cached_candidate_exists(candidate_id):
            candidate = get_cached_candidate(candidate_id)

            # Convert candidate profile to LinkedInProfile object
            profile = LinkedInProfile(**candidate["profile"])

            # Analyze career metrics
            profile.analyze_career()

            candidate["profile"] = profile.dict()

            # Update candidate in Firestore
            create_candidate(candidate)

        logging.info(f"Candidate {candidate_id} updated successfully.")
    except Exception as e:
        logging.error(f"Error processing candidate {candidate_id}: {str(e)}")


def update_all_candidates_parallel(max_workers=100):
    try:
        # Fetch all candidate IDs from Firestore
        candidate_ids = [doc.id for doc in db.collection("candidates").stream()]

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tasks for each candidate
            futures = {
                executor.submit(process_candidate, candidate_id): candidate_id
                for candidate_id in candidate_ids
            }

            # Wait for all tasks to complete
            for future in as_completed(futures):
                candidate_id = futures[future]
                try:
                    future.result()  # Raise any exceptions that occurred during processing
                except Exception as e:
                    logging.error(
                        f"Error processing candidate {candidate_id}: {str(e)}"
                    )

        logging.info("All candidates updated successfully.")
    except Exception as e:
        logging.error(f"Error updating candidates: {str(e)}")


if __name__ == "__main__":
    update_all_candidates_parallel()
