from typing import List, Dict, Optional
import asyncio
from fastapi import HTTPException, status
from services.proxycurl import get_linkedin_profile
import services.firestore as firestore
from models import KeyTrait, Candidate
import psutil
import logging
from datetime import datetime
from fastapi.concurrency import run_in_threadpool
from services.evaluate import run_graph
import re


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

    def _extract_linkedin_id(self, url: str) -> Optional[str]:
        """Extract the LinkedIn public identifier from a profile URL."""
        try:
            # Remove any query parameters
            url = url.split("?")[0]
            # Remove trailing slash if present
            url = url.rstrip("/")
            # Get the last part of the URL which should be the ID
            match = re.search(r"linkedin\.com/in/([^/]+)", url)
            return match.group(1) if match else None
        except Exception:
            return None

    async def process_single_candidate(self, candidate_data: Dict) -> None:
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

            if not candidate_data:
                raise ValueError(
                    f"Could not fetch LinkedIn profile for {candidate_data['url']}"
                )

            # Run evaluation with all the necessary data
            graph_result = await run_graph(
                job_description=self.job_data["job_description"],
                candidate_context=candidate_data["context"],
                candidate_full_name=candidate_data["name"],
                profile=candidate_data["profile"],
                key_traits=key_traits,
                ideal_profiles=self.job_data["ideal_profiles"],
                number_of_queries=candidate_data.get("number_of_queries", 0),
                confidence_threshold=candidate_data.get("confidence_threshold", 0.0),
                search_mode=candidate_data.get("search_mode", True),
                cached=candidate_data.get("cached", False),
                citations=candidate_data.get("citations"),
                source_str=candidate_data.get("source_str"),
            )

            # Always update candidate data and create in Firestore
            update_data = {"profile": graph_result["candidate_profile"]}

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

    def get_candidate_record(self, candidate_data: Dict) -> Optional[Dict]:
        """Get candidate record from LinkedIn URL."""
        try:
            public_id = self._extract_linkedin_id(candidate_data["url"])
            if not public_id:
                print(
                    f"Could not extract public identifier from {candidate_data['url']}"
                )
                return None

            # Check cache first
            if firestore.check_cached_candidate_exists(public_id):
                cached_candidate = firestore.get_cached_candidate(public_id)
                # Use cached data but preserve search_mode from request
                candidate_data.update(
                    {
                        "context": cached_candidate["context"],
                        "name": cached_candidate["name"],
                        "profile": cached_candidate["profile"],
                        "public_identifier": public_id,
                        "source_str": cached_candidate["source_str"],
                        "citations": cached_candidate["citations"],
                        "cached": True,
                    }
                )
                return candidate_data

            # Only call ProxyCurl if not cached
            full_name, profile, public_id = get_linkedin_profile(candidate_data["url"])
            if not profile:
                return None

            candidate_data.update(
                {
                    "context": profile.to_context_string(),
                    "name": full_name,
                    "profile": profile,
                    "public_identifier": public_id,
                    "cached": False,
                }
            )
            return candidate_data
        except Exception as e:
            print(str(e))
            return None

    async def process_urls(self, urls: List[str], search_mode: bool = True) -> None:
        """Process a list of LinkedIn URLs in bulk."""
        try:
            logging.info(f"Processing {len(urls)} LinkedIn URLs")
            candidates = []
            for url in urls:
                candidate_data = Candidate(
                    url=url, search_mode=search_mode
                ).model_dump()

                candidate_data = await run_in_threadpool(
                    lambda: self.get_candidate_record(candidate_data)
                )
                if not candidate_data:
                    logging.error(f"Failed to fetch LinkedIn profile for {url}")
                    continue

                candidates.append(candidate_data)

            logging.info(f"Successfully fetched {len(candidates)} profiles")
            tasks = [
                self.process_single_candidate(candidate) for candidate in candidates
            ]
            await asyncio.gather(*tasks)
        except Exception as e:
            logging.error(str(e))
