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


class Job(BaseModel):
    avoid_traits: list[str]
    benefits: list[str]
    company_about: str
    company_description: str
    company_locations: list[str]
    company_name: str
    equity: str
    experience_info: str
    ideal_candidate: str
    name: str
    paraform_link: str
    recruiting_advice: str
    requirements: list[str]
    responsibilities: list[str]
    role_description: str
    role_locations: list[str]
    salary_lower_bound: int
    salary_upper_bound: int
    tech_stack: list[str]
    visa_text: str
    visa_text_more: str
    workplace: str
    years_experience_max: str
    years_experience_min: str

    def __str__(self):
        return f"""
                {self.company_name} - {self.name}

                Role Overview:
                {self.role_description}

                Requirements:
                • {', '.join(self.requirements)}

                Responsibilities:
                • {', '.join(self.responsibilities)}

                Ideal Candidate:
                {self.ideal_candidate}

                Experience:
                • Required: {self.years_experience_min} - {self.years_experience_max} years
                • Details: {self.experience_info}

                Tech Stack:
                • {', '.join(self.tech_stack)}

                Company Information:
                • About: {self.company_about}
                • Description: {self.company_description}

                • Things to Note: {', '.join(self.avoid_traits)}

                Recruiting Notes:
                {self.recruiting_advice}

""".strip()


class CandidateInfo(BaseModel):
    context: str
    full_name: str
    summary: str


class SearchState(BaseModel):
    source_str: str
    search_queries: list[SearchQuery]
    citations_str: str


class SectionRating(BaseModel):
    section: str
    score: int
    content: str


class Recommendation(BaseModel):
    score: float
    content: str


class JobEvaluation(BaseModel):
    company_name: str
    role: str
    sections: Annotated[list[SectionRating], operator.add]
    recommendation: Recommendation
    markdown: str


class EvaluationState(TypedDict):
    source_str: str
    job_description: str
    candidate_context: str
    candidate_full_name: str
    key_traits: List[str]
    number_of_queries: int
    search_queries: List[SearchQuery]
    completed_sections: Annotated[list, operator.add]   # This is for parallelizing section writing
    validated_sources: Annotated[list, operator.add]   # This is for parallelizing source validation
    recommendation: str
    final_evaluation: str
    section: str   # This is for parallelizing section writing
    source: str   # This is for parallelizing source validation
    sources_dict: dict
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
    candidate: CandidateInfo
    search: SearchState
    relevant_jobs: list[Job]
    current_job: Job
    job_index: int
    evaluations: Annotated[list[JobEvaluation], operator.add]
    recommendation: Recommendation
    number_of_roles: int
    current_section: str
    completed_sections: Annotated[list[SectionRating], operator.add]


class ParaformEvaluationInputState(TypedDict):
    candidate_context: str
    candidate_full_name: str
    number_of_roles: int


class ParaformEvaluationOutputState(TypedDict):
    final_evaluation: dict


class JobOutputState(TypedDict):
    evaluations: list[JobEvaluation]
