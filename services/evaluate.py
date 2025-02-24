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
    search_mode: bool = False,
    cached: bool = False,
    citations: list[dict] = [],
    source_str: str = "",
    custom_instructions: str = None,
) -> EvaluationOutputState:
    """Run the evaluation graph with optional search mode and caching."""
    search_graph = RemoteRunnable(os.getenv("SEARCH_ENDPOINT"))
    eval_graph = RemoteRunnable(os.getenv("EVAL_ENDPOINT"))

    if search_mode:
        if not cached or source_str == "linkedin_only":
            return await search_graph.ainvoke(
                SearchInputState(
                    profile=profile,
                    job=job,
                    number_of_queries=number_of_queries,
                    confidence_threshold=confidence_threshold,
                    custom_instructions=custom_instructions,
                )
            )
        else:
            return await eval_graph.ainvoke(
                EvaluationInputState(
                    source_str=source_str,
                    profile=profile,
                    job=job,
                    citations=citations,
                    custom_instructions=custom_instructions,
                )
            )
    else:
        return await eval_graph.ainvoke(
            EvaluationInputState(
                source_str="",
                profile=profile,
                job=job,
                citations=[],
                custom_instructions=custom_instructions,
            )
        )
    