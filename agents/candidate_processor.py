from typing import List, Dict, Optional
import asyncio
from fastapi import HTTPException, status
from agents.linkedin_processor import get_linkedin_profile_with_companies
import services.firestore as firestore
from models.jobs import KeyTrait, Candidate, CalibratedProfiles, PipelineFeedback
import psutil
import logging
from datetime import datetime, UTC
from services.evaluate import run_graph
from services.firestore import get_custom_instructions
from utils.linkedin_utils import extract_linkedin_id
import uuid
from fastapi.concurrency import run_in_threadpool
from models.api import CandidateCalibrationPayload
from models.jobs import Job
from models.linkedin import LinkedInProfile


class CandidateProcessor:
    def __init__(self, job_id: str, job_data: dict, user_id: str):
        self.job_id = job_id
        self.job_data = job_data
        self.user_id = user_id
        self.default_settings = {
            "number_of_queries": 5,
            "confidence_threshold": 0.5,
            "search_mode": True,  # Default to search mode enabled
        }
        logging.info(
            f"[MEMORY] Initializing CandidateProcessor - {self._get_memory_usage()}"
        )

    def _get_memory_usage(self) -> str:
        """Get current memory usage details"""
        process = psutil.Process()
        memory_info = process.memory_info()
        return (
            f"Time: {datetime.now().isoformat()} | "
            f"RSS: {memory_info.rss / 1024 / 1024:.2f}MB | "
            f"VMS: {memory_info.vms / 1024 / 1024:.2f}MB"
        )

    async def process_single_candidate(self, candidate_data: Dict) -> None:
        """Process a single candidate with evaluation"""
        try:
            logging.info(
                f"[MEMORY] Starting candidate processing - {self._get_memory_usage()}"
            )

            # Check if this is a reevaluation by seeing if the candidate is already in the job
            is_reevaluation = firestore.check_candidate_in_job(
                self.job_id, candidate_data["public_identifier"], self.user_id
            )

            firestore.add_candidate_to_job(
                self.job_id,
                candidate_data["public_identifier"],
                self.user_id,
                {"status": "processing", "name": candidate_data["name"]},
            )

            if not candidate_data:
                raise ValueError(
                    f"Could not fetch LinkedIn profile for {candidate_data['url']}"
                )

            if not isinstance(candidate_data["profile"], LinkedInProfile):
                candidate_data["profile"] = LinkedInProfile(**candidate_data["profile"])

            # Run evaluation with all the necessary data
            graph_result = await run_graph(
                profile=candidate_data["profile"],
                number_of_queries=candidate_data.get("number_of_queries", 0),
                confidence_threshold=candidate_data.get("confidence_threshold", 0.0),
                search_mode=candidate_data.get("search_mode", True),
                cached=candidate_data.get("cached", False),
                citations=candidate_data.get("citations"),
                source_str=candidate_data.get("source_str"),
                custom_instructions=(
                    get_custom_instructions(self.user_id).evaluation_instructions
                    if get_custom_instructions(self.user_id)
                    else ""
                ),
                job=Job(
                    job_description=self.job_data["job_description"],
                    key_traits=[
                        KeyTrait(**trait) for trait in self.job_data["key_traits"]
                    ],
                    calibrated_profiles=[
                        CalibratedProfiles(**profile)
                        for profile in (self.job_data.get("calibrated_profiles") or [])
                    ],
                    job_title=self.job_data["job_title"],
                    company_name=self.job_data["company_name"],
                    created_at=self.job_data.get("created_at"),
                    pipeline_feedback=[
                        PipelineFeedback(**feedback)
                        for feedback in (self.job_data.get("pipeline_feedback") or [])
                    ],
                ),
            )

            profile = candidate_data["profile"]

            if isinstance(profile, LinkedInProfile):
                profile = profile.dict()

            # Always update candidate data and create in Firestore
            update_data = {"profile": profile}

            if candidate_data.get("search_mode", True):
                # In search mode, update citations and source_str from graph result
                update_data.update(
                    {
                        "citations": graph_result["citations"],
                        "source_str": graph_result["source_str"],
                    }
                )
            elif not candidate_data.get("cached", False):
                # In non-search mode, only set linkedin_only if not cached
                update_data.update(
                    {
                        "citations": [],
                        "source_str": "linkedin_only",
                    }
                )

            candidate_data.update(update_data)
            firestore.create_candidate(candidate_data)

            logging.info(f"[MEMORY] After graph search - {self._get_memory_usage()}")

            candidate_job_data = {
                "status": "complete",
                "sections": graph_result["sections"],
                "summary": graph_result["summary"],
                "required_met": graph_result["required_met"],
                "optional_met": graph_result["optional_met"],
                "search_mode": candidate_data.get("search_mode", True),
                "fit": graph_result["fit"],
                "favorite": False,
            }

            firestore.add_candidate_to_job(
                self.job_id,
                candidate_data["public_identifier"],
                self.user_id,
                candidate_job_data,
            )

            # Only decrement search credits if this is not a reevaluation
            if not is_reevaluation:
                firestore.decrement_search_credits(self.user_id)

            logging.info(
                f"[MEMORY] Completed candidate processing - {self._get_memory_usage()}"
            )
        except Exception as e:
            logging.error(f"[MEMORY] Error in processing - {self._get_memory_usage()}")
            firestore.remove_candidate_from_job(
                self.job_id, candidate_data["public_identifier"], self.user_id
            )
            print(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error running candidate evaluation: {str(e)}",
            )

    def get_candidate_record(self, candidate_data: Dict) -> Optional[Dict]:
        """Get candidate record from LinkedIn URL with enriched company data."""
        try:
            public_id = extract_linkedin_id(candidate_data["url"])
            if not public_id:
                print(
                    f"Could not extract public identifier from {candidate_data['url']}"
                )
                return None

            # Check cache first
            if firestore.check_cached_candidate_exists(public_id):
                cached_candidate = firestore.get_cached_candidate(public_id)
                if not cached_candidate.get("name"):
                    logging.error(
                        f"No name found for {candidate_data['url']}, using full name from ProxyCurl"
                    )
                else:
                    # Use cached data but preserve search_mode from request
                    search_mode = candidate_data.get("search_mode", True)
                    candidate_data.update(
                        {
                            "context": cached_candidate["context"],
                            "name": cached_candidate["name"],
                            "profile": cached_candidate["profile"],
                            "public_identifier": public_id,
                            "source_str": cached_candidate["source_str"],
                            "citations": cached_candidate["citations"],
                            "cached": True,
                            "search_mode": search_mode,
                        }
                    )
                    return candidate_data
            else:
                # Only call ProxyCurl if not cached
                (
                    full_name,
                    profile,
                    public_id,
                ) = get_linkedin_profile_with_companies(candidate_data["url"])
                if not full_name or not profile:
                    logging.error(
                        f"No full name or profile found for {candidate_data['url']}, skipping"
                    )
                    return None

                # Preserve search_mode when updating data
                search_mode = candidate_data.get("search_mode", True)
                candidate_data.update(
                    {
                        "context": profile.to_context_string(),
                        "name": full_name,
                        "profile": profile,
                        "public_identifier": public_id,
                        "cached": False,
                        "search_mode": search_mode,
                    }
                )
                return candidate_data
        except Exception as e:
            print(f"Error getting candidate record: {str(e)}")
            return None

    async def process_urls(self, urls: List[str], search_mode: bool = True) -> None:
        """Process a list of LinkedIn URLs in bulk."""
        try:
            logging.info(f"Processing {len(urls)} LinkedIn URLs")

            dummy_id = self.create_dummy_candidate(len(urls))

            # Create all candidate data objects first
            candidate_data_list = [
                Candidate(url=url, search_mode=search_mode).model_dump() for url in urls
            ]
            for data in candidate_data_list:
                data["search_mode"] = search_mode

            # Process URL fetches concurrently using gather
            fetch_tasks = [
                run_in_threadpool(lambda d=data: self.get_candidate_record(d))
                for data in candidate_data_list
            ]
            candidates = await asyncio.gather(*fetch_tasks)

            # Filter out failed fetches
            candidates = [c for c in candidates if c is not None]

            logging.info(f"Successfully fetched {len(candidates)} profiles")

            # Process candidates concurrently
            eval_tasks = [
                self.process_single_candidate(candidate) for candidate in candidates
            ]
            await asyncio.gather(*eval_tasks)

        except Exception as e:
            logging.error(str(e))
        finally:
            firestore.delete_candidate(dummy_id)
            firestore.remove_candidate_from_job(self.job_id, dummy_id, self.user_id)

    async def reevaluate_candidates(self):
        """Reevaluate all candidates for a job"""
        candidates = firestore.get_candidates(self.job_id, self.user_id)
        tasks = [self.process_single_candidate(candidate) for candidate in candidates]
        await asyncio.gather(*tasks)

    def create_dummy_candidate(self, num_urls: int) -> str:
        id = str(uuid.uuid4())
        firestore.create_candidate({"public_identifier": id})
        firestore.add_candidate_to_job(
            self.job_id,
            id,
            self.user_id,
            {
                "status": "processing",
                "name": f"Loading {num_urls} candidates...",
                "is_loading_indicator": True,
            },
        )
        return id

    async def apply_pipeline_feedback(
        self, feedback: str, settings: Optional[Dict] = None
    ) -> None:
        """Apply pipeline-level feedback and recalibrate all candidates"""
        try:
            logging.info("Applying pipeline feedback and recalibrating candidates")

            # Update job data with feedback
            if "pipeline_feedback" not in self.job_data:
                self.job_data["pipeline_feedback"] = []

            self.job_data["pipeline_feedback"].append(
                {"feedback": feedback, "timestamp": datetime.now(UTC).isoformat()}
            )

            if settings:
                self.job_data.update(settings)

            # Update job in Firestore
            firestore.edit_job(self.job_id, self.user_id, self.job_data)

            # Recalibrate all candidates
            await self.reevaluate_candidates()

        except Exception as e:
            logging.error(f"Error applying pipeline feedback: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error applying pipeline feedback: {str(e)}",
            )

    async def calibrate_candidate(
        self,
        candidate_id: str,
        fit: str,
        reasoning: str,
    ) -> None:
        """Calibrate a single candidate and optionally update evaluation settings"""
        try:
            # Get candidate data
            candidate = firestore.get_full_candidate(
                self.job_id, candidate_id, self.user_id
            )
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with id {candidate_id} not found",
                )

            # Update job_data to include calibrated candidate info
            if "calibrated_profiles" not in self.job_data:
                self.job_data["calibrated_profiles"] = []

            # Create a CalibratedProfiles object
            new_calibration = {
                "url": candidate.get("url", ""),
                "fit": fit,
                "reasoning": reasoning,
                "profile": candidate.get("profile"),
                "type": "pipeline",  # Mark as pipeline calibration
            }

            # Update an existing record if it exists, otherwise append
            existing = next(
                (
                    item
                    for item in self.job_data["calibrated_profiles"]
                    if item.get("url") == candidate.get("url")
                ),
                None,
            )
            if existing:
                existing.update(new_calibration)
            else:
                self.job_data["calibrated_profiles"].append(new_calibration)

            # Persist the updated job_data in Firestore
            firestore.edit_job(self.job_id, self.user_id, self.job_data)

            # Re-evaluate all candidates since calibration affects the context
            await self.reevaluate_candidates()

        except Exception as e:
            logging.error(f"Error calibrating candidate: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error calibrating candidate: {str(e)}",
            )

    async def bulk_calibrate_candidates(
        self, feedback: Dict[str, CandidateCalibrationPayload]
    ) -> None:
        """Calibrate multiple candidates in bulk"""
        try:
            # Process each candidate's calibration data first
            for candidate_id, calibration_data in feedback.items():
                # Get candidate data
                candidate = firestore.get_full_candidate(
                    self.job_id, candidate_id, self.user_id
                )
                if not candidate:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Candidate with id {candidate_id} not found",
                    )

                # Update job_data to include calibrated candidate info
                if "calibrated_profiles" not in self.job_data:
                    self.job_data["calibrated_profiles"] = []

                # Create a CalibratedProfiles object
                new_calibration = {
                    "url": candidate.get("url", ""),
                    "fit": calibration_data.fit,
                    "reasoning": calibration_data.reasoning,
                    "profile": candidate.get("profile"),
                    "type": "pipeline",  # Mark as pipeline calibration
                }

                # Update an existing record if it exists, otherwise append
                existing = next(
                    (
                        item
                        for item in self.job_data["calibrated_profiles"]
                        if item.get("url") == candidate.get("url")
                    ),
                    None,
                )
                if existing:
                    existing.update(new_calibration)
                else:
                    self.job_data["calibrated_profiles"].append(new_calibration)

            # Persist all updates to job_data in Firestore
            firestore.edit_job(self.job_id, self.user_id, self.job_data)

            # Perform a single reevaluation of all candidates
            await self.reevaluate_candidates()

        except Exception as e:
            logging.error(f"Error in bulk calibration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error in bulk calibration: {str(e)}",
            )
