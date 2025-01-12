from typing import List, Dict, Any
import asyncio
import csv
from fastapi import HTTPException, status
from services.proxycurl import get_linkedin_context
import services.firestore as firestore
from agents.evaluate_graph import run_search
from models import KeyTrait
import psutil
import logging
from datetime import datetime


class CandidateProcessor:
    def __init__(self, job_id: str, job_data: dict, user_id: str):
        self.job_id = job_id
        self.job_data = job_data
        self.user_id = user_id
        self.default_settings = {
            "number_of_queries": 5,
            "confidence_threshold": 0.5,
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
            search_credits = firestore.get_search_credits(self.user_id)
            if search_credits <= 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You have no search credits remaining",
                )
            # Create the candidate in Firebase first with processing status
            firestore.create_candidate(self.job_id, candidate_data, self.user_id)

            # Convert key_traits from dict to KeyTrait objects
            key_traits = [KeyTrait(**trait) for trait in self.job_data["key_traits"]]

            graph_result = await run_search(
                self.job_data["job_description"],
                candidate_data["context"],
                candidate_data["name"],
                key_traits,  # Pass the KeyTrait objects
                candidate_data["number_of_queries"],
                candidate_data["confidence_threshold"],
            )
            logging.info(f"[MEMORY] After graph search - {self._get_memory_usage()}")

            # Update the candidate with evaluation results
            candidate_data.update(
                {
                    "sections": graph_result["sections"],
                    "citations": graph_result["citations"],
                    "status": "complete",
                    "summary": graph_result["summary"],
                    "overall_score": graph_result["overall_score"],
                }
            )

            firestore.decrement_search_credits(self.user_id)

            # Update the candidate in Firebase with complete status and results
            firestore.create_candidate(self.job_id, candidate_data, self.user_id)
            logging.info(
                f"[MEMORY] Completed candidate processing - {self._get_memory_usage()}"
            )
        except Exception as e:
            logging.error(f"[MEMORY] Error in processing - {self._get_memory_usage()}")
            firestore.delete_candidate(
                self.job_id, candidate_data["public_identifier"], self.user_id
            )
            print(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error running candidate evaluation: {str(e)}",
            )

    async def process_batch(self, candidates: List[Dict[str, Any]]) -> None:
        """Process a batch of candidates concurrently"""
        logging.info(
            f"[MEMORY] Starting batch processing of {len(candidates)} candidates - {self._get_memory_usage()}"
        )
        tasks = [self.process_single_candidate(candidate) for candidate in candidates]
        await asyncio.gather(*tasks)
        logging.info(
            f"[MEMORY] Completed batch processing - {self._get_memory_usage()}"
        )

    def create_candidate_record(self, candidate_data: dict) -> dict:
        """Create initial candidate record from LinkedIn URL"""
        try:
            if not all(
                k in candidate_data and candidate_data[k]
                for k in ["name", "context", "public_identifier"]
            ):
                name, context, public_identifier = get_linkedin_context(
                    candidate_data["url"]
                )
                candidate_data["name"] = name
                candidate_data["context"] = context
                candidate_data["public_identifier"] = public_identifier
            return {
                "status": "processing",
                **self.default_settings,
                **candidate_data,
            }
        except Exception as e:
            print(f"Error processing LinkedIn URL {candidate_data['url']}: {str(e)}")
            return None

    async def process_urls(self, urls: List[str]) -> dict:
        """Process a list of LinkedIn URLs"""
        logging.info(
            f"[MEMORY] Starting URL processing for {len(urls)} URLs - {self._get_memory_usage()}"
        )
        total_urls = len(urls)

        # Start background processing immediately
        asyncio.create_task(self._process_urls_background(urls))
        logging.info(
            f"[MEMORY] Completed URL processing setup - {self._get_memory_usage()}"
        )

        return {
            "message": f"Bulk processing started for {total_urls} LinkedIn profiles",
            "total": total_urls,
        }

    async def _process_urls_background(self, urls: List[str]) -> None:
        """Background processing of URLs"""
        candidates = []
        processed_urls = 0

        for url in urls:
            candidate = self.create_candidate_record({"url": url})
            if candidate:
                candidates.append(candidate)
                firestore.create_candidate(self.job_id, candidate, self.user_id)
                processed_urls += 1

        # Process the candidates in batch
        await self.process_batch(candidates)

    async def process_csv(self, file_str) -> dict:
        """Process candidates from CSV file"""
        total_rows = len(file_str.splitlines()) - 1  # Subtract header row

        # Start background processing immediately
        asyncio.create_task(self._process_csv_background(file_str))

        return {
            "message": f"Processing started for {total_rows} candidates from CSV",
            "total": total_rows,
        }

    async def _process_csv_background(self, file_str) -> None:
        """Background processing of CSV data"""
        csvReader = csv.DictReader(file_str.splitlines())
        candidates = []
        processed_rows = 0

        for row in csvReader:
            if url := row.get("url"):
                candidate = self.create_candidate_record({"url": url})
                if candidate:
                    candidates.append(candidate)
                    firestore.create_candidate(self.job_id, candidate, self.user_id)
                    processed_rows += 1

        # Process the candidates in batch
        await self.process_batch(candidates)
