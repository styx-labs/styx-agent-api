from google.cloud import firestore
import os
import dotenv
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
import sys
from services.search_credits import free_searches

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


def create_job(job_data: dict, user_id: str) -> str:
    """Create a job under the user's collection"""
    emb_text = job_data["job_title"] + " " + job_data["job_description"]
    job_data["embedding"] = Vector(
        get_azure_openai()
        .embeddings.create(
            model="text-embedding-3-small",
            input=emb_text,
        )
        .data[0]
        .embedding
    )
    doc_ref = db.collection("users").document(user_id).collection("jobs").document()
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
    """Delete a job and all its candidates"""
    job_ref = (
        db.collection("users").document(user_id).collection("jobs").document(job_id)
    )

    # Delete all candidates first
    candidates_ref = job_ref.collection("candidates")
    delete_collection(candidates_ref)

    # Then delete the job
    job_ref.delete()
    return True


def create_candidate(job_id: str, candidate_data: dict, user_id: str) -> str:
    """Create a candidate under a specific job"""
    doc_ref = (
        db.collection("users")
        .document(user_id)
        .collection("jobs")
        .document(job_id)
        .collection("candidates")
    )
    if "public_identifier" in candidate_data:
        doc_ref = doc_ref.document(candidate_data["public_identifier"])
        candidate_data["id"] = candidate_data["public_identifier"]
    else:
        doc_ref = doc_ref.document()
        candidate_data["id"] = doc_ref.id
    doc_ref.set(candidate_data)
    return doc_ref.id


def get_candidates(job_id: str, user_id: str) -> list:
    """Get all candidates for a specific job"""
    candidates = []
    candidates_ref = (
        db.collection("users")
        .document(user_id)
        .collection("jobs")
        .document(job_id)
        .collection("candidates")
        .stream()
    )
    for doc in candidates_ref:
        candidate = doc.to_dict()
        candidate["id"] = doc.id
        candidates.append(candidate)
    return candidates


def get_candidate(job_id: str, candidate_id: str, user_id: str) -> dict:
    """Get a specific candidate for a job"""
    doc_ref = (
        db.collection("users")
        .document(user_id)
        .collection("jobs")
        .document(job_id)
        .collection("candidates")
        .document(candidate_id)
    )
    return doc_ref.get().to_dict()


def delete_candidate(job_id: str, candidate_id: str, user_id: str) -> bool:
    """Delete a specific candidate"""
    doc_ref = (
        db.collection("users")
        .document(user_id)
        .collection("jobs")
        .document(job_id)
        .collection("candidates")
        .document(candidate_id)
    )
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
