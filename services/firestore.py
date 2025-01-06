from google.cloud import firestore
import os
import dotenv
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.azure_openai import get_azure_openai

dotenv.load_dotenv()

db = firestore.Client(database=os.getenv("DB"))


def create_job(job_data):
    ref = db.collection("jobs")

    # Add a new document with a generated ID
    doc_ref = ref.document()
    job_data["id"] = doc_ref.id
    doc_ref.set(job_data)

    return doc_ref.id

def delete_job(job_id):
    db.collection("jobs").document(job_id).delete()
    return True

def get_jobs():
    ref = db.collection("jobs")
    docs = ref.stream()
    return [doc.to_dict() for doc in docs]

def get_job(job_id):
    ref = db.collection("jobs").document(job_id)
    doc = ref.get()
    return doc.to_dict()

def create_candidate(job_id, candidate_data):
    ref = db.collection("jobs").document(job_id).collection("candidates")
    if "url" in candidate_data:
        doc_ref = ref.document(candidate_data["public_identifier"])
        candidate_data["id"] = candidate_data["public_identifier"]
    else:
        doc_ref = ref.document()
        candidate_data["id"] = doc_ref.id
    doc_ref.set(candidate_data)
    return candidate_data["id"]

def get_candidates(job_id):
    ref = db.collection("jobs").document(job_id).collection("candidates")
    docs = ref.stream()
    return [doc.to_dict() for doc in docs]

def delete_candidate(job_id, candidate_id):
    db.collection("jobs").document(job_id).collection("candidates").document(candidate_id).delete()
    return True

def get_paraform_jobs():
    ref = db.collection("paraform-jobs")
    docs = ref.stream()
    return [doc.to_dict() for doc in docs]

def get_most_similar_jobs(query, num_jobs):
    ref = db.collection("paraform-jobs")
    azure_openai = get_azure_openai()
    embedding = azure_openai.embeddings.create(input=query, model="text-embedding-3-small").data[0].embedding
    query = ref.find_nearest(
        vector_field="embedding",
        query_vector=Vector(embedding),
        distance_measure=DistanceMeasure.COSINE,
        limit=num_jobs
    )
    return [doc.to_dict() for doc in query.stream()]