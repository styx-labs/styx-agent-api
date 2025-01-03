from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import services.firestore as firestore
from models import (
    Job,
    JobDescription,
    Candidate,
    HeadlessEvaluatePayload,
)
from dotenv import load_dotenv
from services.proxycurl import get_linkedin_context
from agents.evaluate_graph import run_search
from agents.search_helper import get_key_traits


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/evaluate-headless")
async def evaluate_headless(
    payload: HeadlessEvaluatePayload,
):
    candidate_data = payload.model_dump()
    if candidate_data.get("url"):
        name, context = get_linkedin_context(candidate_data["url"])
        candidate_data["name"] = name
        candidate_data["context"] = context

    if not candidate_data["job_description"]:
        candidate_data["key_traits"] = [
            "Technical Skills",
            "Experience",
            "Education",
            "Entrepreneurship",
        ]
    else:
        candidate_data["key_traits"] = get_key_traits(candidate_data["job_description"]).key_traits

    return await run_search(
        job_description=candidate_data["job_description"],
        candidate_context=candidate_data["context"],
        candidate_full_name=candidate_data["name"],
        key_traits=candidate_data["key_traits"],
        number_of_queries=candidate_data["number_of_queries"],
        confidence_threshold=candidate_data["confidence_threshold"],
    )


@app.post("/get-key-traits")
def get_key_traits_request(job_description: JobDescription) -> dict:
    return get_key_traits(job_description.description)


@app.post("/jobs")
def create_job(job: Job):
    job_data = job.model_dump()
    job_id = firestore.create_job(job_data)
    return {"job_id": job_id}


@app.get("/jobs")
def get_jobs():
    jobs = firestore.get_jobs()
    return {"jobs": jobs}


@app.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    success = firestore.delete_job(job_id)
    return {"success": success}


@app.post("/jobs/{job_id}/candidates")
async def create_candidate(job_id: str, candidate: Candidate):
    candidate_data = candidate.model_dump()
    if "url" in candidate_data:
        name, context = get_linkedin_context(candidate_data["url"])
        candidate_data["name"] = name
        candidate_data["context"] = context
    job_data = firestore.get_job(job_id)
    graph_result = await run_search(
        job_data["job_description"],
        candidate_data["context"],
        candidate_data["name"],
        job_data["key_traits"],
        candidate_data["number_of_queries"],
        candidate_data["confidence_threshold"],
    )
    candidate_data["sections"] = graph_result["sections"]
    candidate_data["citations"] = graph_result["citations"]
    candidate_id = firestore.create_candidate(job_id, candidate_data)
    return {"candidate_id": candidate_id}


@app.get("/jobs/{job_id}/candidates")
def get_candidates(job_id: str):
    candidates = firestore.get_candidates(job_id)
    return {"candidates": candidates}


@app.delete("/jobs/{job_id}/candidates/{candidate_id}")
def delete_candidate(job_id: str, candidate_id: str):
    success = firestore.delete_candidate(job_id, candidate_id)
    return {"success": success}
