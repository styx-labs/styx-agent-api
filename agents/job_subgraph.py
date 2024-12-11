from agents.types import EvaluationState, JobOutputState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send
from langgraph.graph import StateGraph, START, END
from services.azure_openai import llm


def write_section(state: EvaluationState):
    """Modified to handle single job"""
    job = state["current_job"]
    sections = []

    for requirement in state["sections"]:
        content = write_section_content(
            section=requirement,
            job=job,
            candidate_full_name=state["candidate_full_name"],
            candidate_context=state["candidate_context"],
            source_str=state["source_str"],
        )
        sections.append({"section": requirement, "content": content})

    return {"completed_sections": sections}


def initiate_section_writing(state: EvaluationState):
    sections = []
    for job in state["relevant_jobs"]:
        for requirement in job["requirements"]:
            sections.append(
                Send(
                    "write_section",
                    {
                        "section": requirement,
                        "job": job,
                        "company_name": job["company_name"],
                        "role": job["name"],
                    },
                )
            )
    return sections


def write_section_content(
    section: str,
    job: str,
    candidate_full_name: str,
    candidate_context: str,
    source_str: str,
):
    section_writer_instructions = """
    You are an expert at evaluating candidates for a job.
    You are given a specific trait that you are evaluating the candidate on.
    You are also given a string of sources that contain information about the candidate.
    Write a evaluation of the candidate in this specific trait based on the provided information.
    It is possible that the candidate does not have any experience that matches the trait - if this is the case, please note this in your evaluation.
    
    Each source is cited by a number.
    When you mention information that you get from a source, please include a citation in your evaluation by citing the number of the source that links to the url in a clickable markdown format.
    For example, if you use information from sources 3 and 7, cite them like this: [[3]](url), [[7]](url). 
    Don't include a citation if you are not referencing a source.

    Guidlines for writing:
    - Strict 50-150 word limit
    - No marketing language
    - Technical focus
    - Write in simple, clear language
    - Start with your most important insight in **bold**
    - Use short paragraphs (2-3 sentences max)
    - Use Markdown format for headings, bold, etc. Use ### for the section heading, which should be "Evaluation of <trait>".

    Here is the trait you are evaluating the candidate on:
    {section} for {current_job}
    Here is the candidate's name:
    {candidate_full_name}
    Here is the candidate's basic profile:
    {candidate_context}
    Here are the sources about the candidate:
    {source_str}
    """

    content = llm.invoke(
        [
            SystemMessage(
                content=section_writer_instructions.format(
                    current_job=job,
                    section=section,
                    candidate_full_name=candidate_full_name,
                    candidate_context=candidate_context,
                    source_str=source_str,
                )
            )
        ]
        + [
            HumanMessage(
                content=f"Write a evaluation of the candidate in this specific trait based on the provided information."
            )
        ]
    )

    return content.content


def write_recommendation(state: EvaluationState):
    candidate_full_name = state["candidate_full_name"]
    completed_sections = state["completed_sections"]
    current_job = state["current_job"]

    completed_sections_str = "\n\n".join([s["content"] for s in completed_sections])

    recommmendation_instructions = """
    You are an expert at evaluating candidates for a job.
    You are given a specific job description and a report evaluating specific areas of the candidate.
    Write a recommendation on how good of a fit the candidate is for the job that is based on the information provided.
    This should be a short 2-3 sentence evaluation on how well the candidate fits the job description based on the information provided.
    Do not include any evidence from the sources in your evaluation.

    Please write the recommendation in Markdown format, starting the section with a heading: ## Overall Evaluation

    Here is the job description:
    {current_job}

    Here is the candidate's name:
    {candidate_full_name}

    Here is the report about the candidate:
    {completed_sections}
    """

    formatted_prompt = recommmendation_instructions.format(
        current_job=current_job,
        candidate_full_name=candidate_full_name,
        completed_sections=completed_sections_str,
    )
    content = llm.invoke(
        [SystemMessage(content=formatted_prompt)]
        + [
            HumanMessage(
                content=f"Write a recommendation on how good of a fit the candidate is for the job based on the provided information."
            )
        ]
    )

    return {
        "completed_sections": [
            {"section": "recommendation", "content": content.content}
        ]
    }


def compile_job_evaluation(state: EvaluationState):
    """Compiles evaluation for a single job"""
    sections = state["completed_sections"]
    company_name = state["company_name"]
    role = state["role"]

    # Create structured evaluation object
    evaluation = {
        "company_name": company_name,
        "role": role,
        "sections": [
            {"section": section["section"], "content": section["content"]}
            for section in sections
        ],
        # Keep the markdown version for backwards compatibility
        "markdown": f"# Evaluation for {role} at {company_name}\n\n"
        + "\n\n".join(section["content"] for section in sections),
    }

    return {"evaluations": [evaluation]}


## Subgraph
def create_job_evaluation_subgraph(job_index: int):
    """Creates a subgraph for evaluating a single job"""
    builder = StateGraph(EvaluationState, output=JobOutputState)

    # Add nodes specific to this job
    builder.add_node(f"write_section_{job_index}", write_section)
    builder.add_node(f"write_recommendation_{job_index}", write_recommendation)
    builder.add_node(f"compile_job_evaluation_{job_index}", compile_job_evaluation)

    # Connect nodes
    builder.add_edge(START, f"write_section_{job_index}")
    builder.add_edge(f"write_section_{job_index}", f"write_recommendation_{job_index}")
    builder.add_edge(
        f"write_recommendation_{job_index}", f"compile_job_evaluation_{job_index}"
    )
    builder.add_edge(f"compile_job_evaluation_{job_index}", END)

    return builder.compile()
