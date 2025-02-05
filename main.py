from fastapi import (
    FastAPI,
    HTTPException,
    status,
    Header,
    Depends,
    BackgroundTasks,
    Request,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
import services.firestore as firestore
from models.base import Job, JobDescription, KeyTrait
from models.api import (
    Candidate,
    BulkLinkedInPayload,
    ReachoutPayload,
    GetEmailPayload,
    CheckoutSessionRequest,
    EditKeyTraitsPayload,
    TestTemplateRequest,
)
from dotenv import load_dotenv
from services.get_secret import get_secret
from services.proxycurl import get_email, get_linkedin_profile
from agents.helper_functions import (
    get_key_traits,
    get_reachout_message,
    get_list_of_profiles,
)
from services.firebase_auth import verify_firebase_token
from agents.candidate_processor import CandidateProcessor
from services.stripe import create_checkout_session
import logging
import sys
import stripe
from typing import Optional, List
from services.firestore import (
    get_user_templates,
    set_user_templates,
    get_custom_instructions,
    set_custom_instructions,
)
from models.templates import UserTemplates
from models.instructions import CustomInstructions


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


@app.post("/get-key-traits")
async def get_key_traits_request(
    job_description: JobDescription, user_id: str = Depends(validate_user_id)
):
    try:
        ideal_profiles = await get_list_of_profiles(job_description.ideal_profile_urls)
        key_traits_output = get_key_traits(job_description.description, ideal_profiles)
        key_traits_output = key_traits_output.model_dump()
        key_traits_output["ideal_profiles"] = ideal_profiles
        return key_traits_output
    except Exception as e:
        print(e)
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


@app.patch("/jobs/{job_id}/edit-key-traits")
def edit_key_traits(
    job_id: str,
    payload: EditKeyTraitsPayload,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(validate_user_id),
):
    try:
        firestore.edit_key_traits(job_id, user_id, payload.model_dump())
        job_data = firestore.get_job(job_id, user_id)
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found",
        )

    processor = CandidateProcessor(job_id, job_data, user_id)
    background_tasks.add_task(processor.reevaluate_candidates)

    return {"message": "Candidate processing started"}


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
            user_id=user_id,
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

    background_tasks.add_task(processor.process_urls, [candidate.url])
    return {"message": "Candidate processing started"}


@app.post("/jobs/{job_id}/candidates_bulk")
async def create_candidates_bulk(
    job_id: str,
    background_tasks: BackgroundTasks,
    payload: BulkLinkedInPayload,
    user_id: str = Depends(validate_user_id),
):
    search_credits = firestore.get_search_credits(user_id)
    num_urls = len(payload.urls)

    if search_credits < num_urls:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient search credits. You have {search_credits} credits but need {num_urls} credits to process all URLs.",
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
def get_candidates(
    job_id: str,
    filter_traits: Optional[List[str]] = Query(
        None, description="List of traits to filter by"
    ),
    user_id: str = Depends(validate_user_id),
):
    try:
        candidates = firestore.get_candidates(job_id, user_id, filter_traits)
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
        name, profile, public_identifier = get_linkedin_profile(url)
        return {
            "name": name,
            "context": profile.to_context_string(),
            "profile": profile,
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
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving search credits: {str(e)}",
        )


@app.get("/show-popup")
def show_popup(user_id: str = Depends(validate_user_id)):
    try:
        return {"show_popup": firestore.show_popup(user_id)}
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving search credits: {str(e)}",
        )


@app.post("/set-popup-shown")
def set_popup_shown(user_id: str = Depends(validate_user_id)):
    try:
        firestore.set_popup_shown(user_id)
        return {"success": True}
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting popup shown: {str(e)}",
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
                payload_str, sig_header, get_secret("stripe-webhook-secret", "1")
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


@app.put("/settings/templates", response_model=UserTemplates)
async def update_user_templates(
    templates: UserTemplates,
    user_id: str = Depends(validate_user_id),
):
    """Update user's templates"""
    return set_user_templates(user_id, templates)


@app.get("/settings/templates", response_model=UserTemplates)
async def get_all_user_templates(
    user_id: str = Depends(validate_user_id),
):
    """Get user's templates"""
    return get_user_templates(user_id)


@app.put("/settings/evaluation-instructions", response_model=CustomInstructions)
async def update_evaluation_instructions(
    instructions: CustomInstructions,
    user_id: str = Depends(validate_user_id),
):
    """Update user's custom evaluation instructions"""
    return set_custom_instructions(user_id, instructions)


@app.get("/settings/evaluation-instructions", response_model=CustomInstructions)
async def get_evaluation_instructions(
    user_id: str = Depends(validate_user_id),
):
    """Get user's custom evaluation instructions"""
    return get_custom_instructions(user_id)


@app.post("/test-reachout-template")
async def test_reachout_template(
    request: TestTemplateRequest,
    user_id: str = Depends(validate_user_id),
):
    """Test a reach out message template using sample data"""
    try:
        # Use fake candidate and job data for testing
        fake_candidate = {
            "name": "Alex Thompson",
            "sections": [
                {
                    "section": "Current Role",
                    "content": "Senior Software Engineer at Tech Corp, leading a team of 5 engineers in building scalable cloud solutions",
                },
                {
                    "section": "Technical Skills",
                    "content": "Expertise in Python, React, and AWS. Strong background in distributed systems and microservices architecture",
                },
                {
                    "section": "Leadership Experience",
                    "content": "3 years of team leadership experience, mentoring junior developers and managing project deliverables",
                },
            ],
            "citations": [
                {
                    "distilled_content": "Led migration of monolithic application to microservices, improving system reliability by 40%"
                },
                {
                    "distilled_content": "Implemented CI/CD pipeline reducing deployment time from 2 hours to 15 minutes"
                },
                {
                    "distilled_content": "Regular speaker at tech conferences on cloud architecture and system design"
                },
            ],
        }

        fake_job = {
            "job_description": """
            We're seeking a Senior Software Engineer to join our growing team. The ideal candidate will:
            - Have strong experience in cloud technologies and distributed systems
            - Lead and mentor junior developers
            - Drive technical architecture decisions
            - Have excellent communication skills
            
            Required Skills:
            - 5+ years of software development experience
            - Strong knowledge of Python and modern web frameworks
            - Experience with cloud platforms (AWS/GCP/Azure)
            - Track record of leading technical projects
            """
        }

        # Generate message with test template
        reachout = get_reachout_message(
            name=fake_candidate["name"],
            job_description=fake_job["job_description"],
            sections=fake_candidate["sections"],
            citations=fake_candidate["citations"],
            format=request.format,
            template_content=request.template_content,
        )

        return {
            "reachout": reachout,
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing reachout template: {str(e)}",
        )


@app.post("/jobs/{job_id}/candidates/{candidate_id}/favorite")
def toggle_favorite(
    job_id: str, candidate_id: str, user_id: str = Depends(validate_user_id)
):
    try:
        new_favorite_status = firestore.toggle_candidate_favorite(job_id, candidate_id, user_id)
        return {"favorite": new_favorite_status}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle favorite status: {str(e)}",
        )
