from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import services.firestore as firestore
from models import (
    Job,
    JobDescription,
    Candidate,
    HeadlessEvaluatePayload,
    HeadlessReachoutPayload,
)
from dotenv import load_dotenv
from services.proxycurl import get_linkedin_context
from agents.evaluate_graph import run_search
from services.helper_functions import get_key_traits, get_reachout_message


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
    try:
        candidate_data = payload.model_dump()
        if candidate_data.get("url"):
            try:
                name, context = get_linkedin_context(candidate_data["url"])
                candidate_data["name"] = name
                candidate_data["context"] = context
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to fetch LinkedIn profile: {str(e)}"
                )

        if not candidate_data["job_description"]:
            candidate_data["key_traits"] = [
                "Technical Skills",
                "Experience",
                "Education",
                "Entrepreneurship",
            ]
        else:
            try:
                candidate_data["key_traits"] = get_key_traits(candidate_data["job_description"]).key_traits
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error generating key traits: {str(e)}"
                )

        return await run_search(
            job_description=candidate_data["job_description"],
            candidate_context=candidate_data["context"],
            candidate_full_name=candidate_data["name"],
            key_traits=candidate_data["key_traits"],
            number_of_queries=candidate_data["number_of_queries"],
            confidence_threshold=candidate_data["confidence_threshold"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing evaluation: {str(e)}"
        )
    

@app.post("/generate-reachout-headless")
async def generate_reachout_headless(payload: HeadlessReachoutPayload):
    try:
        return get_reachout_message(
            name=payload.name,
            job_description=payload.job_description,
            sections=payload.sections,
            citations=payload.citations
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating reachout message: {str(e)}"
        )


@app.post("/get-key-traits")
def get_key_traits_request(job_description: JobDescription):
    try:
        return get_key_traits(job_description.description)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating key traits: {str(e)}"
        )


@app.post("/jobs")
def create_job(job: Job):
    try:
        job_data = job.model_dump()
        job_id = firestore.create_job(job_data)
        return {"job_id": job_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )


@app.get("/jobs")
def get_jobs():
    try:
        jobs = firestore.get_jobs()
        return {"jobs": jobs}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving jobs: {str(e)}"
        )


@app.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    try:
        success = firestore.delete_job(job_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to delete job: {str(e)}"
        )


async def temp_create_candidate(job_id: str, candidate_data: dict, job_data: dict):
    try:
        graph_result = await run_search(
            job_data["job_description"],
            candidate_data["context"],
            candidate_data["name"],
            job_data["key_traits"],
            candidate_data["number_of_queries"],
            candidate_data["confidence_threshold"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running candidate evaluation: {str(e)}"
        )
    
    candidate_data["sections"] = graph_result["sections"]
    candidate_data["citations"] = graph_result["citations"]
    candidate_data["status"] = "complete"
    candidate_data["summary"] = graph_result["summary"]
    candidate_data["overall_score"] = graph_result["overall_score"]
    firestore.create_candidate(job_id, candidate_data)


@app.post("/jobs/{job_id}/candidates")
async def create_candidate(job_id: str, candidate: Candidate, background_tasks: BackgroundTasks):
    try:
        candidate_data = candidate.model_dump()
        if "url" in candidate_data:
            try:
                name, context, public_identifier = get_linkedin_context(candidate_data["url"])
                candidate_data["name"] = name
                candidate_data["context"] = context
                candidate_data["public_identifier"] = public_identifier
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to fetch LinkedIn profile: {str(e)}"
                )
        
        job_data = firestore.get_job(job_id)
        if not job_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found"
            )
        
        candidate_data["status"] = "processing"
        firestore.create_candidate(job_id, candidate_data)

        background_tasks.add_task(temp_create_candidate, job_id, candidate_data, job_data)
        return {"message": "Candidate processing started"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating candidate: {str(e)}"
        )


@app.get("/jobs/{job_id}/candidates")
def get_candidates(job_id: str):
    try:
        candidates = firestore.get_candidates(job_id)
        return {"candidates": candidates}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving candidates: {str(e)}"
        )


@app.delete("/jobs/{job_id}/candidates/{candidate_id}")
def delete_candidate(job_id: str, candidate_id: str):
    try:
        success = firestore.delete_candidate(job_id, candidate_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete candidate: {str(e)}"
        )


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    try:
        job = firestore.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found"
            )
        return job
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving job: {str(e)}"
        )
