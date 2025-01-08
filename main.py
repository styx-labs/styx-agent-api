from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    status,
    Header,
    Depends,
    File,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
import services.firestore as firestore
from models import (
    Job,
    JobDescription,
    Candidate,
    HeadlessEvaluatePayload,
    HeadlessReachoutPayload,
    BulkLinkedInPayload,
)
from dotenv import load_dotenv
from services.proxycurl import get_linkedin_context
from agents.evaluate_graph import run_search
from services.helper_functions import get_key_traits, get_reachout_message
from services.firebase_auth import verify_firebase_token
import asyncio
from agents.candidate_processor import CandidateProcessor


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def validate_user_id(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
        )

    try:
        # Check if the authorization header starts with "Bearer "
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Must start with 'Bearer'",
            )

        # Extract the token
        token = authorization.split(" ")[1]

        # Verify the Firebase token
        user_id = await verify_firebase_token(token)
        return user_id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
        )


@app.post("/evaluate-headless")
async def evaluate_headless(
    payload: HeadlessEvaluatePayload, user_id: str = Depends(validate_user_id)
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
                    detail=f"Failed to fetch LinkedIn profile: {str(e)}",
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
                candidate_data["key_traits"] = get_key_traits(
                    candidate_data["job_description"]
                ).key_traits
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error generating key traits: {str(e)}",
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
            detail=f"Error processing evaluation: {str(e)}",
        )


@app.post("/generate-reachout-headless")
async def generate_reachout_headless(
    payload: HeadlessReachoutPayload, user_id: str = Depends(validate_user_id)
):
    try:
        return get_reachout_message(
            name=payload.name,
            job_description=payload.job_description,
            sections=payload.sections,
            citations=payload.citations,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating reachout message: {str(e)}",
        )


@app.post("/get-key-traits")
def get_key_traits_request(
    job_description: JobDescription, user_id: str = Depends(validate_user_id)
):
    try:
        return get_key_traits(job_description.description)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating key traits: {str(e)}",
        )


@app.post("/jobs")
def create_job(job: Job, user_id: str = Depends(validate_user_id)):
    try:
        job_data = job.model_dump()
        job_id = firestore.create_job(job_data, user_id)
        return {"job_id": job_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}",
        )


@app.get("/jobs")
def get_jobs(user_id: str = Depends(validate_user_id)):
    try:
        jobs = firestore.get_jobs(user_id)
        return {"jobs": jobs}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving jobs: {str(e)}",
        )


@app.delete("/jobs/{job_id}")
def delete_job(job_id: str, user_id: str = Depends(validate_user_id)):
    try:
        success = firestore.delete_job(job_id, user_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(e)}",
        )


@app.post("/jobs/{job_id}/candidates")
async def create_candidate(
    job_id: str,
    candidate: Candidate,
    user_id: str = Depends(validate_user_id),
):
    try:
        job_data = firestore.get_job(job_id, user_id)
        if not job_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found",
            )

        processor = CandidateProcessor(job_id, job_data, user_id)
        candidate_data = candidate.model_dump()

        if "url" in candidate_data:
            candidate_data = processor.create_candidate_record(candidate_data["url"])
            if not candidate_data:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch LinkedIn profile",
                )

        # Start background processing
        asyncio.create_task(processor.process_single_candidate(candidate_data))
        return {"message": "Candidate processing started"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating candidate: {str(e)}",
        )


@app.post("/jobs/{job_id}/candidates_batch")
async def create_candidates_batch(
    job_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(validate_user_id),
):
    try:
        job_data = firestore.get_job(job_id, user_id)
        if not job_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found",
            )

        processor = CandidateProcessor(job_id, job_data, user_id)
        return await processor.process_csv(file.file)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating candidates batch: {str(e)}",
        )


@app.post("/jobs/{job_id}/candidates_bulk")
async def create_candidates_bulk(
    job_id: str,
    payload: BulkLinkedInPayload,
    user_id: str = Depends(validate_user_id),
):
    try:
        job_data = firestore.get_job(job_id, user_id)
        if not job_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found",
            )

        processor = CandidateProcessor(job_id, job_data, user_id)
        return await processor.process_urls(payload.urls)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing bulk LinkedIn URLs: {str(e)}",
        )


@app.get("/jobs/{job_id}/candidates")
def get_candidates(job_id: str, user_id: str = Depends(validate_user_id)):
    try:
        candidates = firestore.get_candidates(job_id, user_id)
        return {"candidates": candidates}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving candidates: {str(e)}",
        )


@app.delete("/jobs/{job_id}/candidates/{candidate_id}")
def delete_candidate(
    job_id: str, candidate_id: str, user_id: str = Depends(validate_user_id)
):
    try:
        success = firestore.delete_candidate(job_id, candidate_id, user_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete candidate: {str(e)}",
        )


@app.get("/jobs/{job_id}")
def get_job(job_id: str, user_id: str = Depends(validate_user_id)):
    try:
        job = firestore.get_job(job_id, user_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found",
            )
        return job
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving job: {str(e)}",
        )
