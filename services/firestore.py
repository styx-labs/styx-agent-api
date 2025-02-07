from google.cloud import firestore
import os
import dotenv
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
import sys
from agents.search_credits import free_searches
from datetime import datetime, timedelta, UTC
from typing import List, Dict, Optional
from models.templates import UserTemplates
from models.instructions import CustomInstructions

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.azure_openai import get_azure_openai

dotenv.load_dotenv()

db = firestore.Client(database=os.getenv("DB"))


def get_search_credits(user_id: str) -> int:
    """Get the number of search credits remaining for a user"""
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    user_dict = doc.to_dict() if doc.exists else {}
    if "search_credits" not in user_dict:
        user_dict["search_credits"] = free_searches
        doc_ref.set(user_dict)
    return user_dict["search_credits"]


def show_popup(user_id: str) -> bool:
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    user_dict = doc.to_dict() if doc.exists else {}
    if "show_popup" not in user_dict:
        user_dict["show_popup"] = True
        doc_ref.set(user_dict)
    return user_dict["show_popup"]


def set_popup_shown(user_id: str):
    doc_ref = db.collection("users").document(user_id)
    doc_ref.update({"show_popup": False})


def decrement_search_credits(user_id: str) -> int:
    """Decrement the number of search credits remaining for a user"""
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    user_dict = doc.to_dict() if doc.exists else {}
    if "search_credits" not in user_dict:
        user_dict["search_credits"] = free_searches
    user_dict["search_credits"] -= 1
    doc_ref.set(user_dict)
    return user_dict["search_credits"]


def edit_key_traits(job_id: str, user_id: str, key_traits: dict):
    """Edit the key traits for a job"""
    doc_ref = (
        db.collection("users").document(user_id).collection("jobs").document(job_id)
    )
    doc_ref.update(key_traits)


def create_job(job_data: dict, user_id: str) -> str:
    """Create a job under the user's collection with optimized embedding"""
    # Generate document reference first to avoid extra writes
    doc_ref = db.collection("users").document(user_id).collection("jobs").document()

    # Generate embedding
    emb_text = f"{job_data['job_title']} {job_data['job_description']}"
    job_data["embedding"] = Vector(
        get_azure_openai()
        .embeddings.create(
            model="text-embedding-3-small",
            input=emb_text,
        )
        .data[0]
        .embedding
    )

    # Single write operation
    doc_ref.set(job_data)
    return doc_ref.id


def get_jobs(user_id: str) -> list:
    """Get all jobs for a specific user"""
    jobs = []
    jobs_ref = db.collection("users").document(user_id).collection("jobs").stream()
    for doc in jobs_ref:
        job = doc.to_dict()
        job["id"] = doc.id
        jobs.append(job)
    return jobs


def get_jobs_recommend(user_id: str, context: str) -> list:
    """Get most similar jobs for a specific user"""
    emb = (
        get_azure_openai()
        .embeddings.create(
            model="text-embedding-3-small",
            input=context,
        )
        .data[0]
        .embedding
    )
    jobs = []
    jobs_ref = (
        db.collection("users")
        .document(user_id)
        .collection("jobs")
        .find_nearest(
            vector_field="embedding",
            query_vector=Vector(emb),
            distance_measure=DistanceMeasure.EUCLIDEAN,
            limit=5,
            distance_result_field="vector_distance",
        )
    )
    for doc in jobs_ref.stream():
        job = doc.to_dict()
        job["id"] = doc.id
        jobs.append(job)
    jobs.sort(key=lambda x: x.get("vector_distance", float("inf")))
    return jobs


def get_job(job_id: str, user_id: str) -> dict:
    """Get a specific job for a user"""
    doc_ref = (
        db.collection("users").document(user_id).collection("jobs").document(job_id)
    )
    doc = doc_ref.get()
    if doc.exists:
        job = doc.to_dict()
        job["id"] = doc.id
        return job
    return None


def delete_job(job_id: str, user_id: str) -> bool:
    """Delete a job and all its candidates efficiently"""
    batch = db.batch()
    job_ref = (
        db.collection("users").document(user_id).collection("jobs").document(job_id)
    )

    # Get all candidates in batches
    candidates_ref = job_ref.collection("candidates")
    batch_size = 500
    docs = candidates_ref.limit(batch_size).stream()

    deleted = 0
    for doc in docs:
        batch.delete(doc.reference)
        deleted += 1

        # Commit batch when size limit reached and start new batch
        if deleted % batch_size == 0:
            batch.commit()
            batch = db.batch()

    # Delete remaining documents and the job itself
    batch.delete(job_ref)
    batch.commit()

    return True


def check_cached_candidate_exists(candidate_id: str):
    """Check if a candidate exists and was updated within the last month"""
    candidate_ref = db.collection("candidates").document(candidate_id)
    doc = candidate_ref.get()
    if not doc.exists:
        return False

    candidate_data = doc.to_dict()
    updated_at = candidate_data.get("updated_at")
    if not updated_at:
        return False

    # Create timezone-aware datetime for comparison
    one_month_ago = datetime.now(UTC) - timedelta(days=30)
    # Firestore timestamp should already be UTC-aware
    return updated_at > one_month_ago


def add_candidate_to_job(
    job_id: str, candidate_id: str, user_id: str, candidate_data: dict
):
    """Add a candidate to a job"""
    job_ref = (
        db.collection("users")
        .document(user_id)
        .collection("jobs")
        .document(job_id)
        .collection("candidates")
        .document(candidate_id)
    )
    job_ref.set(candidate_data)


def remove_candidate_from_job(job_id: str, candidate_id: str, user_id: str):
    """Remove a candidate from a job"""
    job_ref = (
        db.collection("users")
        .document(user_id)
        .collection("jobs")
        .document(job_id)
        .collection("candidates")
        .document(candidate_id)
    )
    job_ref.delete()


def create_candidate(candidate_data: dict) -> str:
    """Create a candidate"""
    candidates_ref = db.collection("candidates")

    if "public_identifier" in candidate_data:
        candidates_ref = candidates_ref.document(candidate_data["public_identifier"])
        candidate_data["id"] = candidate_data["public_identifier"]
    else:
        candidates_ref = candidates_ref.document()
        candidate_data["id"] = candidates_ref.id
    candidates_ref.set(candidate_data)
    return candidates_ref.id


def get_candidates(
    job_id: str, user_id: str, filter_traits: Optional[List[str]] = None
) -> list:
    """Get all candidates for a specific job, sorted by match criteria."""
    # Get all job-specific candidate data in one batch
    candidates_ref = (
        db.collection("users")
        .document(user_id)
        .collection("jobs")
        .document(job_id)
        .collection("candidates")
        .stream()
    )

    # Build lookup of job-specific data
    job_candidates = {doc.id: {**doc.to_dict(), "id": doc.id} for doc in candidates_ref}

    if not job_candidates:
        return []

    # Batch get all base candidate data
    base_refs = [
        db.collection("candidates").document(candidate_id)
        for candidate_id in job_candidates.keys()
    ]
    base_docs = db.get_all(base_refs)

    # Merge data efficiently
    all_candidates = []
    for base in base_docs:
        candidate_data = {}
        if base.exists:
            candidate_data.update(base.to_dict())
        if base.id in job_candidates:
            candidate_data.update(job_candidates[base.id])
        candidate_data["id"] = base.id
        all_candidates.append(candidate_data)

    # Filter by traits if specified
    if filter_traits:
        all_candidates = [
            candidate
            for candidate in all_candidates
            if _meets_trait_requirements(candidate.get("sections", []), filter_traits)
        ]

    # Sort using tuple comparison for efficiency
    return sorted(
        all_candidates,
        key=lambda x: (
            x.get("required_met", 0),
            x.get("optional_met", 0),
            x.get("fit", 0),
        ),
        reverse=True,
    )


def _meets_trait_requirements(sections: List[Dict], required_traits: List[str]) -> bool:
    """Check if candidate meets all required trait requirements."""
    trait_values = {
        section["section"]: section["value"]
        for section in sections
        if isinstance(section, dict) and "section" in section and "value" in section
    }

    return all(
        trait in trait_values and trait_values[trait] is True
        for trait in required_traits
    )


def get_cached_candidate(candidate_id: str) -> dict:
    """Get a cached candidate"""
    candidate_ref = db.collection("candidates").document(candidate_id).get().to_dict()
    return candidate_ref


def get_full_candidate(job_id: str, candidate_id: str, user_id: str) -> dict:
    """Get a specific candidate for a job"""
    candidate_job_ref = (
        db.collection("users")
        .document(user_id)
        .collection("jobs")
        .document(job_id)
        .collection("candidates")
        .document(candidate_id)
        .get()
        .to_dict()
    )
    candidate_ref = db.collection("candidates").document(candidate_id).get().to_dict()
    return {**candidate_ref, **candidate_job_ref}


def delete_candidate(candidate_id: str) -> bool:
    """Delete a specific candidate"""
    doc_ref = db.collection("candidates").document(candidate_id)
    doc_ref.delete()
    return True


def delete_collection(coll_ref, batch_size=500):
    """Helper function to delete a collection"""
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        doc.reference.delete()
        deleted = deleted + 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)


def get_paraform_jobs():
    ref = db.collection("paraform-jobs")
    docs = ref.stream()
    return [doc.to_dict() for doc in docs]


def get_most_similar_jobs(query, num_jobs):
    ref = db.collection("paraform-jobs")
    azure_openai = get_azure_openai()
    embedding = (
        azure_openai.embeddings.create(input=query, model="text-embedding-3-small")
        .data[0]
        .embedding
    )
    query = ref.find_nearest(
        vector_field="embedding",
        query_vector=Vector(embedding),
        distance_measure=DistanceMeasure.COSINE,
        limit=num_jobs,
    )
    return [doc.to_dict() for doc in query.stream()]


def add_search_credits(user_id: str, credits: int) -> int:
    """Add search credits to a user's account and return the new total

    Args:
        user_id: The ID of the user
        credits: The number of credits to add

    Returns:
        The new total number of credits
    """
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    user_dict = doc.to_dict() if doc.exists else {}

    current_credits = user_dict.get("search_credits", 0)
    new_total = current_credits + credits

    user_dict["search_credits"] = new_total
    doc_ref.set(user_dict)

    return new_total


def get_user_templates(user_id: str) -> UserTemplates:
    """Get user's templates"""
    templates_ref = db.collection("users").document(user_id).collection("settings")
    linkedin_doc = templates_ref.document("linkedin_template").get()
    email_doc = templates_ref.document("email_template").get()

    return UserTemplates(
        linkedin_template=linkedin_doc.get("content") if linkedin_doc.exists else None,
        email_template=email_doc.get("content") if email_doc.exists else None,
    )


def set_user_templates(user_id: str, templates: UserTemplates) -> UserTemplates:
    """Set user's templates"""
    templates_ref = db.collection("users").document(user_id).collection("settings")
    batch = db.batch()

    if templates.linkedin_template is not None:
        linkedin_ref = templates_ref.document("linkedin_template")
        batch.set(linkedin_ref, {"content": templates.linkedin_template})

    if templates.email_template is not None:
        email_ref = templates_ref.document("email_template")
        batch.set(email_ref, {"content": templates.email_template})

    batch.commit()
    return get_user_templates(user_id)


def delete_user_templates(user_id: str) -> None:
    """Delete user's templates"""
    templates_ref = db.collection("users").document(user_id).collection("settings")
    batch = db.batch()

    linkedin_ref = templates_ref.document("linkedin_template")
    email_ref = templates_ref.document("email_template")

    batch.delete(linkedin_ref)
    batch.delete(email_ref)

    batch.commit()


def get_custom_instructions(user_id: str) -> CustomInstructions:
    """Get user's custom evaluation instructions"""
    settings_ref = db.collection("users").document(user_id).collection("settings")
    doc = settings_ref.document("evaluation_instructions").get()

    return CustomInstructions(
        evaluation_instructions=doc.get("content") if doc.exists else None
    )


def set_custom_instructions(
    user_id: str, instructions: CustomInstructions
) -> CustomInstructions:
    """Set user's custom evaluation instructions"""
    settings_ref = db.collection("users").document(user_id).collection("settings")

    if instructions.evaluation_instructions is not None:
        settings_ref.document("evaluation_instructions").set(
            {"content": instructions.evaluation_instructions}
        )

    return get_custom_instructions(user_id)


def toggle_candidate_favorite(job_id: str, candidate_id: str, user_id: str) -> bool:
    """Toggle favorite status for a candidate in a job"""
    candidate_ref = (
        db.collection("users")
        .document(user_id)
        .collection("jobs")
        .document(job_id)
        .collection("candidates")
        .document(candidate_id)
    )

    doc = candidate_ref.get()
    if not doc.exists:
        return False

    candidate_data = doc.to_dict()
    current_favorite = candidate_data.get("favorite", False)
    candidate_ref.update({"favorite": not current_favorite})
    return not current_favorite


def bulk_remove_candidates_from_job(
    job_id: str, candidate_ids: List[str], user_id: str
) -> bool:
    """Remove multiple candidates from a job efficiently using batched writes"""
    batch = db.batch()
    batch_size = 500
    deleted = 0

    for candidate_id in candidate_ids:
        job_ref = (
            db.collection("users")
            .document(user_id)
            .collection("jobs")
            .document(job_id)
            .collection("candidates")
            .document(candidate_id)
        )
        batch.delete(job_ref)
        deleted += 1

        # Commit batch when size limit reached and start new batch
        if deleted % batch_size == 0:
            batch.commit()
            batch = db.batch()

    # Commit any remaining deletes
    if deleted % batch_size != 0:
        batch.commit()

    return True


def bulk_favorite_candidates(
    job_id: str, candidate_ids: List[str], user_id: str, favorite_status: bool = True
) -> bool:
    """Set favorite status for multiple candidates efficiently using batched writes"""
    batch = db.batch()
    batch_size = 500
    updated = 0

    for candidate_id in candidate_ids:
        candidate_ref = (
            db.collection("users")
            .document(user_id)
            .collection("jobs")
            .document(job_id)
            .collection("candidates")
            .document(candidate_id)
        )
        batch.update(candidate_ref, {"favorite": favorite_status})
        updated += 1

        # Commit batch when size limit reached and start new batch
        if updated % batch_size == 0:
            batch.commit()
            batch = db.batch()

    # Commit any remaining updates
    if updated % batch_size != 0:
        batch.commit()

    return True
