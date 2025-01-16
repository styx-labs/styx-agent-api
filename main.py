from fastapi import (
    FastAPI,
    HTTPException,
    status,
    Header,
    Depends,
    BackgroundTasks,
    Request,
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
    ReachoutPayload,
    GetEmailPayload,
    CheckoutSessionRequest,
)
from dotenv import load_dotenv
import os
from services.proxycurl import get_linkedin_context, get_email
from agents.evaluate_graph import run_search
from services.helper_functions import get_key_traits, get_reachout_message
from services.firebase_auth import verify_firebase_token
from agents.candidate_processor import CandidateProcessor
from services.stripe import create_checkout_session
import logging
import sys
from fastapi.concurrency import run_in_threadpool
import stripe


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.CRITICAL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
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


@app.post("/jobs_recommend")
def get_jobs_recommend(context: str, user_id: str = Depends(validate_user_id)):
    try:
        jobs = firestore.get_jobs_recommend(user_id, context)
        return {"jobs": jobs}
    except Exception as e:
        print(e)
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


@app.post("/jobs/{job_id}/candidates/{candidate_id}/generate-reachout")
async def generate_reachout(
    job_id: str,
    candidate_id: str,
    payload: ReachoutPayload,
    user_id: str = Depends(validate_user_id),
):
    try:
        job = firestore.get_job(job_id, user_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with id {job_id} not found",
            )
        candidate = firestore.get_full_candidate(job_id, candidate_id, user_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with id {candidate_id} not found",
            )

        reachout = get_reachout_message(
            name=candidate["name"],
            job_description=job["job_description"],
            sections=candidate["sections"],
            citations=candidate["citations"],
            format=payload.format,
        )
        return {"reachout": reachout}
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating reachout message: {str(e)}",
        )


@app.post("/jobs/{job_id}/candidates")
async def create_candidate(
    job_id: str,
    candidate: Candidate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(validate_user_id),
):
    search_credits = firestore.get_search_credits(user_id)
    if search_credits <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="You have no search credits remaining",
        )

    job_data = firestore.get_job(job_id, user_id)
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found",
        )

    processor = CandidateProcessor(job_id, job_data, user_id)
    candidate_data = candidate.model_dump()

    candidate_data = await run_in_threadpool(
        lambda: processor.get_candidate_record(candidate_data)
    )
    if not candidate_data:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch LinkedIn profile",
        )

    background_tasks.add_task(processor.process_single_candidate, candidate_data)

    return {"message": "Candidate processing started"}


@app.post("/jobs/{job_id}/candidates_bulk")
async def create_candidates_bulk(
    job_id: str,
    background_tasks: BackgroundTasks,
    payload: BulkLinkedInPayload,
    user_id: str = Depends(validate_user_id),
):
    search_credits = firestore.get_search_credits(user_id)
    required_credits = len(payload.urls)

    if search_credits < required_credits:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient search credits. You have {search_credits} credits but need {required_credits} credits to process all URLs.",
        )

    job_data = firestore.get_job(job_id, user_id)
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found",
        )

    processor = CandidateProcessor(job_id, job_data, user_id)

    background_tasks.add_task(processor.process_urls, payload.urls)
    return {"message": "Candidates processing started"}


@app.get("/jobs/{job_id}/candidates")
def get_candidates(job_id: str, user_id: str = Depends(validate_user_id)):
    try:
        candidates = firestore.get_candidates(job_id, user_id)
        return {"candidates": candidates}
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving candidates: {str(e)}",
        )


@app.delete("/jobs/{job_id}/candidates/{candidate_id}")
def delete_candidate(
    job_id: str, candidate_id: str, user_id: str = Depends(validate_user_id)
):
    try:
        success = firestore.remove_candidate_from_job(job_id, candidate_id, user_id)
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


@app.post("/get_linkedin_context")
def get_linkedin_context_request(url: str, user_id: str = Depends(validate_user_id)):
    try:
        name, context, public_identifier = get_linkedin_context(url)
        return {
            "name": name,
            "context": context,
            "public_identifier": public_identifier,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving LinkedIn context: {str(e)}",
        )


@app.post("/get-email")
def get_email_request(
    payload: GetEmailPayload, user_id: str = Depends(validate_user_id)
):
    try:
        email = get_email(payload.linkedin_profile_url)
        return {"email": email}
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving email: {str(e)}",
        )


@app.post("/get-search-credits")
def get_search_credits(user_id: str = Depends(validate_user_id)):
    try:
        return {"search_credits": firestore.get_search_credits(user_id)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving search credits: {str(e)}",
        )


@app.post("/payments/create-checkout-session")
def create_checkout_session_endpoint(
    payload: CheckoutSessionRequest, user_id: str = Depends(validate_user_id)
):
    try:
        checkout_url = create_checkout_session(payload.planId, user_id)
        return {"url": checkout_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating checkout session: {str(e)}",
        )


@app.post("/webhook")
async def stripe_webhook(request: Request):
    try:
        # Get the raw request body as bytes
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        if not sig_header:
            raise HTTPException(status_code=400, detail="No signature header")

        try:
            # Convert payload to string if it's bytes
            if isinstance(payload, bytes):
                payload_str = payload.decode("utf-8")
            else:
                payload_str = payload

            event = stripe.Webhook.construct_event(
                payload_str, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

        # Handle the event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]

            # Get user ID and plan from metadata
            user_id = session.get("metadata", {}).get("user_id")
            plan_id = session.get("metadata", {}).get("plan_id")

            if not user_id or not plan_id:
                raise HTTPException(
                    status_code=400,
                    detail="Missing user_id or plan_id in session metadata",
                )

            # Determine credits based on plan
            credits_to_add = 100 if plan_id.lower() == "basic" else 500

            # Add credits to user's account
            new_total = firestore.add_search_credits(user_id, credits_to_add)

            return {"status": "success", "new_credit_total": new_total}

        return {"status": "success", "type": event["type"]}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}",
        )
