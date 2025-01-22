from langserve import RemoteRunnable
from agents.types import (
    EvaluationInputState,
    EvaluationOutputState,
    CachedEvaluationInputState,
)
import os
from datamodels.linkedin import LinkedInProfile


async def run_graph(
    job_description: str,
    candidate_context: str,
    candidate_full_name: str,
    profile: LinkedInProfile,
    key_traits: list[dict],
    number_of_queries: int = 0,
    confidence_threshold: float = 0.0,
    search_mode: bool = True,
    cached: bool = False,
    citations: list[dict] = None,
    source_str: str = None,
) -> EvaluationOutputState:
    """Run the evaluation graph with optional search mode and caching."""
    remote_graph = RemoteRunnable(os.getenv("EVAL_ENDPOINT"))

    # If cached and has citations/source_str, use cached evaluation
    if cached and citations is not None and source_str is not None:
        # Unless in search mode and only LinkedIn data
        if not (search_mode and source_str == "linkedin_only"):
            return await remote_graph.ainvoke(
                CachedEvaluationInputState(
                    job_description=job_description,
                    candidate_context=candidate_context,
                    candidate_profile=profile,
                    candidate_full_name=candidate_full_name,
                    key_traits=key_traits,
                    citations=citations,
                    source_str=source_str,
                )
            )

    # Otherwise do a fresh evaluation
    remote_graph = RemoteRunnable(os.getenv("SEARCH_ENDPOINT" if search_mode else "EVAL_ENDPOINT"))
    input_state = (
        EvaluationInputState(
            job_description=job_description,
            candidate_context=candidate_context,
            candidate_profile=profile,
            candidate_full_name=candidate_full_name,
            key_traits=key_traits,
            number_of_queries=number_of_queries,
            confidence_threshold=confidence_threshold,
            search_mode=search_mode,
        )
        if search_mode
        else CachedEvaluationInputState(
            job_description=job_description,
            candidate_context=candidate_context,
            candidate_profile=profile,
            candidate_full_name=candidate_full_name,
            key_traits=key_traits,
            citations=[],  # No citations in LinkedIn-only mode
            source_str="linkedin_only",
        )
    )
    return await remote_graph.ainvoke(input_state)
