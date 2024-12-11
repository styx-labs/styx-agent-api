from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
from services.azure_openai import get_azure_openai
from agents.prompts import key_traits_prompt
import services.firestore as firestore
from models import Job, JobDescription, Candidate, EvaluateGraphPayload
from dotenv import load_dotenv
from agents.evaluate_graph import run_search

load_dotenv()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/evaluate")
async def evaluate_graph(payload: EvaluateGraphPayload):
    return await run_search(
        candidate_context=payload.candidate_context,
        candidate_full_name=payload.candidate_full_name,
        number_of_queries=payload.number_of_queries,
    )


@app.post("/get-key-traits")
def get_key_traits(job_description: JobDescription):
    client = get_azure_openai()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": key_traits_prompt},
            {"role": "user", "content": job_description.description},
        ],
        response_format={"type": "json_object"},
    )
    traits = json.loads(response.choices[0].message.content)["key_traits"]
    return {"key_traits": traits}


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
    job_data = firestore.get_job(job_id)
    graph_result = await run_search(
        job_data["job_description"],
        candidate_data["context"],
        candidate_data["name"],
        job_data["key_traits"],
        10,
    )
    candidate_data["result"] = graph_result["final_evaluation"]
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
