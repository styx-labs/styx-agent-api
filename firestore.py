from google.cloud import firestore
import os
import dotenv

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
    doc_ref = ref.document()
    candidate_data["id"] = doc_ref.id
    doc_ref.set(candidate_data)
    return doc_ref.id

def get_candidates(job_id):
    ref = db.collection("jobs").document(job_id).collection("candidates")
    docs = ref.stream()
    return [doc.to_dict() for doc in docs]

def delete_candidate(job_id, candidate_id):
    db.collection("jobs").document(job_id).collection("candidates").document(candidate_id).delete()
    return True
