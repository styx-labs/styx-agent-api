from typing import List
import asyncio
from fastapi import HTTPException, status
from services.proxycurl import get_linkedin_profile
import services.firestore as firestore
from models import KeyTrait, Candidate
import psutil
import logging
from datetime import datetime
from fastapi.concurrency import run_in_threadpool
from services.evaluate import run_graph, run_graph_cached


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

    async def process_single_candidate(self, candidate_data: dict) -> None:
        """Process a single candidate with evaluation"""
        try:
            logging.info(
                f"[MEMORY] Starting candidate processing - {self._get_memory_usage()}"
            )

            firestore.add_candidate_to_job(
                self.job_id,
                candidate_data["public_identifier"],
                self.user_id,
                {"status": "processing", "name": candidate_data["name"]},
            )

            # Convert key_traits from dict to KeyTrait objects
            key_traits = [KeyTrait(**trait) for trait in self.job_data["key_traits"]]

            if firestore.check_cached_candidate_exists(
                candidate_data["public_identifier"]
            ):
                # Always try to use cached data first
                cached_candidate = firestore.get_cached_candidate(
                    candidate_data["public_identifier"]
                )
                graph_result = await run_graph_cached(
                    self.job_data["job_description"],
                    candidate_data["context"],
                    candidate_data["name"],
                    candidate_data["profile"],
                    key_traits,
                    cached_candidate["citations"],
                    cached_candidate["source_str"],
                )
            else:
                # If no cache, decide between search or LinkedIn-only mode
                graph_result = await run_graph(
                    self.job_data["job_description"],
                    candidate_data["context"],
                    candidate_data["name"],
                    candidate_data["profile"],
                    key_traits,
                    candidate_data["number_of_queries"],
                    candidate_data["confidence_threshold"],
                    search_mode=candidate_data.get("search_mode", True),
                )

                # Always update candidate data and create in Firestore
                candidate_data.update(
                    {
                        "citations": graph_result["citations"],
                        "source_str": graph_result["source_str"],
                        "profile": graph_result["candidate_profile"],
                    }
                )
                firestore.create_candidate(candidate_data)

            logging.info(f"[MEMORY] After graph search - {self._get_memory_usage()}")

            candidate_job_data = {
                "status": "complete",
                "sections": graph_result["sections"],
                "summary": graph_result["summary"],
                "overall_score": graph_result["overall_score"],
                "search_mode": candidate_data.get(
                    "search_mode", True
                ),  # Add search mode to response
            }

            firestore.add_candidate_to_job(
                self.job_id,
                candidate_data["public_identifier"],
                self.user_id,
                candidate_job_data,
            )
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

    def get_candidate_record(self, candidate_data: dict) -> dict:
        """Create initial candidate record from LinkedIn URL"""
        try:
            if not all(
                k in candidate_data and candidate_data[k]
                for k in ["name", "context", "public_identifier"]
            ):
                name, profile, public_identifier = get_linkedin_profile(
                    candidate_data["url"]
                )
                candidate_data["name"] = name
                candidate_data["profile"] = profile
                candidate_data["context"] = profile.to_context_string()
                candidate_data["public_identifier"] = public_identifier
                return {
                    **self.default_settings,
                    **candidate_data,
                }
        except Exception as e:
            print(f"Error processing LinkedIn URL {candidate_data['url']}: {str(e)}")
            return None

    async def process_urls(self, urls: List[str], search_mode: bool = True) -> None:
        """Process a list of LinkedIn URLs"""
        try:
            print(f"Processing {len(urls)} LinkedIn URLs")
            candidates = []
            for url in urls:
                candidate_data = Candidate(
                    url=url, search_mode=search_mode
                ).model_dump()
                candidate_data = await run_in_threadpool(
                    lambda: self.get_candidate_record(candidate_data)
                )
                if not candidate_data:
                    continue
                candidates.append(candidate_data)
            tasks = [
                self.process_single_candidate(candidate) for candidate in candidates
            ]
            await asyncio.gather(*tasks)
        except Exception as e:
            print(str(e))
