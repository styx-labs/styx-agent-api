from typing import List, Dict, Any
import asyncio
import csv
import codecs
from fastapi import HTTPException, status
from services.proxycurl import get_linkedin_context
import services.firestore as firestore
from agents.evaluate_graph import run_search


class CandidateProcessor:
    def __init__(self, job_id: str, job_data: dict, user_id: str):
        self.job_id = job_id
        self.job_data = job_data
        self.user_id = user_id
        self.default_settings = {
            "number_of_queries": 5,
            "confidence_threshold": 0.5,
        }

    async def process_single_candidate(self, candidate_data: dict) -> None:
        """Process a single candidate with evaluation"""
        try:
            graph_result = await run_search(
                self.job_data["job_description"],
                candidate_data["context"],
                candidate_data["name"],
                self.job_data["key_traits"],
                candidate_data["number_of_queries"],
                candidate_data["confidence_threshold"],
            )

            candidate_data.update(
                {
                    "sections": graph_result["sections"],
                    "citations": graph_result["citations"],
                    "status": "complete",
                    "summary": graph_result["summary"],
                    "overall_score": graph_result["overall_score"],
                }
            )

            firestore.create_candidate(self.job_id, candidate_data, self.user_id)
        except Exception as e:
            if candidate_data.get("public_identifier"):
                firestore.delete_candidate(
                    self.job_id, candidate_data["public_identifier"], self.user_id
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error running candidate evaluation: {str(e)}",
            )

    async def process_batch(self, candidates: List[Dict[str, Any]]) -> None:
        """Process a batch of candidates concurrently"""
        tasks = [self.process_single_candidate(candidate) for candidate in candidates]
        await asyncio.gather(*tasks)

    def create_candidate_record(self, url: str) -> dict:
        """Create initial candidate record from LinkedIn URL"""
        try:
            name, context, public_identifier = get_linkedin_context(url)
            return {
                "url": url,
                "status": "processing",
                "name": name,
                "context": context,
                "public_identifier": public_identifier,
                **self.default_settings,
            }
        except Exception as e:
            print(f"Error processing LinkedIn URL {url}: {str(e)}")
            return None

    async def process_urls(self, urls: List[str]) -> dict:
        """Process a list of LinkedIn URLs"""
        candidates = []
        total_urls = len(urls)
        processed_urls = 0

        for url in urls:
            candidate = self.create_candidate_record(url)
            if candidate:
                candidates.append(candidate)
                firestore.create_candidate(self.job_id, candidate, self.user_id)
                processed_urls += 1

        # Start background processing
        asyncio.create_task(self.process_batch(candidates))

        return {
            "message": f"Bulk processing started: successfully queued {processed_urls} out of {total_urls} LinkedIn profiles",
            "processed": processed_urls,
            "total": total_urls,
        }

    async def process_csv(self, file) -> dict:
        """Process candidates from CSV file"""
        csvReader = csv.DictReader(codecs.iterdecode(file, "utf-8"))
        candidates = []
        total_rows = 0
        processed_rows = 0

        for row in csvReader:
            total_rows += 1
            if url := row.get("url"):
                candidate = self.create_candidate_record(url)
                if candidate:
                    candidates.append(candidate)
                    processed_rows += 1

        # Start background processing
        asyncio.create_task(self.process_batch(candidates))

        return {
            "message": f"Candidates processing started: successfully created {processed_rows} candidates out of {total_rows} candidates"
        }
