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
    number_of_queries: int,
    confidence_threshold: float,
    search_mode: bool = True,
) -> EvaluationOutputState:
    """Run the evaluation graph with optional search mode."""
    if not search_mode:
        remote_graph = RemoteRunnable(os.getenv("EVAL_ENDPOINT"))
        return await remote_graph.ainvoke(
            CachedEvaluationInputState(
                job_description=job_description,
                candidate_context=candidate_context,
                candidate_profile=profile,
                candidate_full_name=candidate_full_name,
                key_traits=key_traits,
                citations=[],  # No citations in LinkedIn-only mode
                source_str="linkedin_only",
            )
        )

    remote_graph = RemoteRunnable(os.getenv("SEARCH_ENDPOINT"))
    return await remote_graph.ainvoke(
        EvaluationInputState(
            job_description=job_description,
            candidate_context=candidate_context,
            candidate_profile=profile,
            candidate_full_name=candidate_full_name,
            key_traits=key_traits,
            number_of_queries=number_of_queries,
            confidence_threshold=confidence_threshold,
            search_mode=True,
        )
    )


async def run_graph_cached(
    job_description: str,
    candidate_context: str,
    candidate_full_name: str,
    profile: LinkedInProfile,
    key_traits: list[dict],
    citations: list[dict],
    source_str: str,
) -> EvaluationOutputState:
    remote_graph = RemoteRunnable(os.getenv("EVAL_ENDPOINT"))
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
