from pydantic import BaseModel, Field
from typing import List, Annotated
from typing_extensions import TypedDict
import operator


class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Query for web search.")


class Queries(BaseModel):
    queries: List[SearchQuery] = Field(
        description="List of search queries.",
    )


class EvaluationState(TypedDict):
    source_str: str
    job_description: str
    candidate_context: str
    candidate_full_name: str
    key_traits: List[str]
    number_of_queries: int
    search_queries: List[SearchQuery]
    completed_sections: Annotated[list, operator.add]
    recommendation: str
    final_evaluation: str
    section: str
    citations: str


class EvaluationInputState(TypedDict):
    job_description: str
    candidate_context: str
    candidate_full_name: str
    key_traits: List[str]
    number_of_queries: int


class EvaluationOutputState(TypedDict):
    citations: str
    sections: List[dict]


class ParaformEvaluationState(TypedDict):
    source_str: str
    job_description: str
    candidate_context: str
    candidate_full_name: str
    number_of_queries: int
    search_queries: List[SearchQuery]
    completed_sections: Annotated[list, operator.add]
    section: str
    sections: List[str]
    citations: str
    candidate_summary: str
    relevant_jobs: List[str]
    current_job: str
    job_index: int
    company_name: str
    evaluations: Annotated[list, operator.add]
    role: str


class ParaformEvaluationInputState(TypedDict):
    candidate_context: str
    candidate_full_name: str
    number_of_queries: int


class ParaformEvaluationOutputState(TypedDict):
    final_evaluation: dict


class JobOutputState(TypedDict):
    evaluations: list[str]
