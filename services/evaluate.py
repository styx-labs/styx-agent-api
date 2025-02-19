from langserve import RemoteRunnable
from models.evaluation import (
    SearchInputState,
    EvaluationOutputState,
    EvaluationInputState,
)
import os
from models.linkedin import LinkedInProfile
from models.jobs import Job


async def run_graph(
    profile: LinkedInProfile,
    job: Job,
    number_of_queries: int = 0,
    confidence_threshold: float = 0.0,
    search_mode: bool = True,
    cached: bool = False,
    citations: list[dict] = None,
    source_str: str = None,
    custom_instructions: str = None,
) -> EvaluationOutputState:
    """Run the evaluation graph with optional search mode and caching."""
    remote_graph = RemoteRunnable(os.getenv("EVAL_ENDPOINT"))

    # If cached and has citations/source_str, use cached evaluation
    if cached and citations is not None and source_str is not None:
        # Unless in search mode and only LinkedIn data
        if not (search_mode and source_str == "linkedin_only"):
            return await remote_graph.ainvoke(
                EvaluationInputState(
                    source_str=source_str,
                    profile=profile,
                    job=job,
                    citations=citations,
                    custom_instructions=custom_instructions,
                )
            )

    # Otherwise do a fresh evaluation
    remote_graph = RemoteRunnable(
        os.getenv("SEARCH_ENDPOINT" if search_mode else "EVAL_ENDPOINT")
    )
    input_state = (
        SearchInputState(
            profile=profile,
            job=job,
            number_of_queries=number_of_queries,
            confidence_threshold=confidence_threshold,
            custom_instructions=custom_instructions,
        )
        if search_mode
        else EvaluationInputState(
            profile=profile,
            job=job,
            source_str="linkedin_only",
            citations=[],  # No citations in LinkedIn-only mode
            custom_instructions=custom_instructions,
        )
    )
    return await remote_graph.ainvoke(input_state)
