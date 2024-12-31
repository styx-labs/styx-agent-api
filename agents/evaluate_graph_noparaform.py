from tavily import TavilyClient, AsyncTavilyClient
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send
from langgraph.graph import START, END, StateGraph
from langsmith import traceable
import os
from typing_extensions import Annotated
import requests
import re
import json
import os
from langchain_core.messages import HumanMessage
from typing import Annotated
import asyncio
import operator
from typing_extensions import TypedDict
from typing import  Annotated, List
from pydantic import BaseModel, Field


llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0,
)

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

report_planner_query_writer_instructions="""You are an expert at researching people online. Your goal is to find detailed information about a candidate for a job opportunity.
The candidate is:
{candidate_full_name}
{candidate_context}
The job they're being considered for is:
{job_description}
Generate {number_of_queries} search queries that will help gather comprehensive information about this candidate. 
Guidelines for creating effective person-focused queries:
1. Create simple, direct queries using key identifying information
2. Avoid complex queries with multiple keywords or technical terms
3. Focus on finding the candidate's digital presence
4. Include queries that might surface profiles, articles, or mentions from:
   - Professional organizations and news
   - University publications
   - Personal blogs
   - GitHug repositories
Make each query specific and focused on one aspect of the candidate's background."""

tavily_async_client = AsyncTavilyClient()

@traceable
async def tavily_search_async(search_queries):
    """
    Performs concurrent web searches using the Tavily API.
    """
    search_tasks = []
    for query in search_queries:
        # Extract the search_query string from the SearchQuery object
        query_str = query.search_query
        search_tasks.append(
            tavily_async_client.search(
                query_str,  # Use the string instead of the SearchQuery object
                max_results=5
            )
        )
    # Execute all searches concurrently
    search_docs = await asyncio.gather(*search_tasks)
    return search_docs

def clean_text(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower())

def heuristic_validator(
    content, title, candidate_full_name: str
) -> bool:
    cleaned_link_text = clean_text(content + " " + title)
    cleaned_candidate_full_name = clean_text(candidate_full_name)
    name_parts = cleaned_candidate_full_name.split()
    score = 0.0
    if cleaned_candidate_full_name in cleaned_link_text:
        score += 1.0
    name_part_matches = sum(
        1 for part in name_parts if f" {part} " in f" {cleaned_link_text} "
    )
    score += (name_part_matches / len(name_parts)) * 0.5
    return score >= 0.5

class LLMValidatorOutput(BaseModel):
    is_valid: bool

async def llm_validator(
    raw_content, candidate_full_name: str, candidate_context: str
) -> bool:
    prompt = """
You are a validator determining if a webpage's content is genuinely about a specific candidate.
Candidate Full Name: {candidate_full_name}
Candidate Profile:
{candidate_context}
Raw Content: {raw_content}
Use the following guidelines to validate if this webpage is about the candidate in question:
1. Name Match:
   - The webpage must explicitly mention the candidate's full name or a clear variation
2. Context Alignment:
   - Current or past employers mentioned in the candidate's profile
   - Educational institutions from the candidate's background
   - Job titles or roles from the candidate's experience
   - Projects or achievements mentioned in the candidate's profile
   - Time periods that align with the candidate's career history
3. Confidence Check:
   - Is there any conflicting information that suggests this might be about a different person?
   - Are there enough specific details to be confident this is about our candidate?
   - Could this content reasonably apply to someone else with the same name?
While you should be very careful in your evaluation, we don't want to reject a valid source. As long as you have reasonable confidence that this is about the candidate in question, you should return True.
    """
    structured_llm = llm.with_structured_output(LLMValidatorOutput)
    output = structured_llm.invoke([SystemMessage(content=prompt.format(candidate_full_name=candidate_full_name, candidate_context=candidate_context, raw_content=raw_content))]+[HumanMessage(content="Validate if this webpage is about the candidate in question.")])
    return output.is_valid

async def distill_source(raw_content, candidate_full_name: str):
    prompt = """
        You will be given a string of raw content from a webpage.
        Please extract the relevant information about the given person from the raw HTML.
        Describe what the source is, what it is about, and how it is relevant to the person, etc.
        Write your response in paragraph form, limited to 200 words.
        Here is the raw content:
        {raw_content}
        Here is the person's full name:
        {candidate_full_name}
    """
    output = llm.invoke([SystemMessage(content=prompt.format(raw_content=raw_content, candidate_full_name=candidate_full_name))]+[HumanMessage(content="Extract the relevant information about the given person from the raw HTML.")])
    return output.content

async def deduplicate_and_format_sources(search_response, max_tokens_per_source, candidate_full_name: str, candidate_context: str):
    """
    Takes either a single search response or list of responses from Tavily API and formats them.
    Limits the raw_content to approximately max_tokens_per_source.
    include_raw_content specifies whether to include the raw_content from Tavily in the formatted string.
    
    Args:
        search_response: Either:
            - A dict with a 'results' key containing a list of search results
            - A list of dicts, each containing search results
            
    Returns:
        str: Formatted string with deduplicated sources
    """
    # Convert input to list of results
    if isinstance(search_response, dict):
        sources_list = search_response['results']
    elif isinstance(search_response, list):
        sources_list = []
        for response in search_response:
            if isinstance(response, dict) and 'results' in response:
                sources_list.extend(response['results'])
            else:
                sources_list.extend(response)
    else:
        raise ValueError("Input must be either a dict with 'results' or a list of search results")
    
    # Deduplicate by URL
    unique_sources = {}
    for source in sources_list:
        if source['url'] not in unique_sources:
            unique_sources[source['url']] = source
    # Create a list of URLs to remove
    urls_to_remove = []
    for source in unique_sources.values():
        try:
            result = requests.get(source['url'], timeout=5)
            content = result.text
            char_limit = max_tokens_per_source * 4
            source['raw_content'] = content[:char_limit] if len(content) > char_limit else content
        except Exception:
            print(f"Error fetching {source['url']}")
            urls_to_remove.append(source['url'])
            continue
    
    # Remove failed URLs after iteration
    for url in urls_to_remove:
        del unique_sources[url]
    valid_sources = {}
    # Validate sources
    for source in unique_sources.values():
        if heuristic_validator(source['content'], source['title'], candidate_full_name):
            if await llm_validator(source['raw_content'], candidate_full_name, candidate_context):
                valid_sources[source['url']] = source
    for source in valid_sources.values():
        source['distilled_content'] = await distill_source(source['raw_content'], candidate_full_name)
    # Format output
    formatted_text = "Sources:\n\n"
    citation_str = "### Citations \n\n"
    for i, source in enumerate(valid_sources.values(), 1):
        formatted_text += f"[{i}]: {source['title']}:\n"
        formatted_text += f"URL: {source['url']}\n"
        formatted_text += f"Relevant content from source: {source['distilled_content']}\n===\n"
        citation_str += f"[{i}] <{source['url']}> \n\n"
                
    return formatted_text.strip(), citation_str

def generate_queries(state: EvaluationState):
    job_description = state["job_description"]
    candidate_context = state["candidate_context"]
    number_of_queries = state["number_of_queries"]
    candidate_full_name = state["candidate_full_name"]
    structured_llm = llm.with_structured_output(Queries)
    system_instructions_query = report_planner_query_writer_instructions.format(job_description=job_description, candidate_full_name=candidate_full_name, candidate_context=candidate_context, number_of_queries=number_of_queries)
    results = structured_llm.invoke([SystemMessage(content=system_instructions_query)]+[HumanMessage(content="Generate search queries.")])
    return {"search_queries": results.queries}

async def gather_sources(state: EvaluationState):
    candidate_context = state["candidate_context"]
    candidate_full_name = state["candidate_full_name"]
    search_queries = state["search_queries"]
    search_docs = await tavily_search_async(search_queries)
    source_str, citation_str = await deduplicate_and_format_sources(search_docs, max_tokens_per_source=10000, candidate_full_name=candidate_full_name, candidate_context=candidate_context)
    return {"source_str": source_str, "citations": citation_str}

def evaluate_trait(state: EvaluationState):
    class EvaluationOutput(BaseModel):
        score: int
        evaluation: str

    evaluation_instructions = """
    You are an expert at evaluating candidates for a job.
    You are given a specific trait that you are evaluating the candidate on.
    You are also given a string of sources that contain information about the candidate.
    Write a evaluation of the candidate in this specific trait based on the provided information.
    It is possible that there is no information about the candidate in this trait - if this is the case, please mention that no information was found regarding the trait, not that the candidate does not have the trait.

    Output two values:
    - An integer score from 0 to 10 that rates the candidate based on their experience in this trait.
    - A string of text that is the evaluation of the candidate in this specific trait based on the provided information. This should be a single sentence that is less than 50 words.

    Here is the trait you are evaluating the candidate on:
    {section}
    Here is the candidate's name:
    {candidate_full_name}
    Here is the candidate's basic profile:
    {candidate_context}
    Here are the sources about the candidate:
    {source_str}
    """

    structured_llm = llm.with_structured_output(EvaluationOutput)

    section = state["section"]
    source_str = state["source_str"]
    candidate_full_name = state["candidate_full_name"]
    candidate_context = state["candidate_context"]
    content = structured_llm.invoke([SystemMessage(content=evaluation_instructions.format(section=section, candidate_full_name=candidate_full_name, candidate_context=candidate_context, source_str=source_str))]+[HumanMessage(content=f"Score and evaluate the candidate in this specific trait based on the provided information.")])
    return {"completed_sections": [{ "section": section, "content": content.evaluation, "score": content.score}]}

def write_recommendation(state: EvaluationState):
    candidate_full_name = state["candidate_full_name"]
    completed_sections = state["completed_sections"]
    job_description = state["job_description"]
    completed_sections_str = "\n\n".join([s["content"] for s in completed_sections])
    overall_score = sum([s["score"] for s in completed_sections])
    recommmendation_instructions = """
    You are an expert at evaluating candidates for a job.
    You are given a specific job description and a report evaluating specific areas of the candidate.
    Write a recommendation on how good of a fit the candidate is for the job that is based on the information provided.
    This should be a short 2-3 sentence evaluation on how well the candidate fits the job description based on the information provided.
    Here is the job description:
    {job_description}
    Here is the candidate's name:
    {candidate_full_name}
    Here is the report about the candidate:
    {completed_sections}
    """
    formatted_prompt = recommmendation_instructions.format(job_description=job_description, candidate_full_name=candidate_full_name, completed_sections=completed_sections_str)
    content = llm.invoke([SystemMessage(content=formatted_prompt)]+[HumanMessage(content=f"Write a recommendation on how good of a fit the candidate is for the job based on the provided information.")])
    return {"completed_sections": [{ "section": "recommendation", "content": content.content, "score": overall_score}]}

def compile_evaluation(state: EvaluationState):
    key_traits = ["recommendation"] + state["key_traits"]
    completed_sections = state["completed_sections"]
    citations = state["citations"]
    ordered_sections = []
    for trait in key_traits:
        for section in completed_sections:
            if section["section"] == trait:
                ordered_sections.append(section)
    return {"sections": ordered_sections, "citations": citations}

def initiate_evaluation(state: EvaluationState):
    return [
        Send("evaluate_trait", {"section": t, **state})
        for t in state["key_traits"]
    ]

async def run_search_(job_description: str, candidate_context: str, candidate_full_name: str, key_traits: List[str], number_of_queries: int):
    builder = StateGraph(EvaluationState, input=EvaluationInputState, output=EvaluationOutputState)
    builder.add_node("generate_queries", generate_queries)
    builder.add_node("gather_sources", gather_sources)
    builder.add_node("evaluate_trait", evaluate_trait)
    builder.add_node("write_recommendation", write_recommendation)
    builder.add_node("compile_evaluation", compile_evaluation)
    builder.add_edge(START, "generate_queries")
    builder.add_edge("generate_queries", "gather_sources")
    builder.add_conditional_edges("gather_sources", initiate_evaluation, ["evaluate_trait"])
    builder.add_edge("evaluate_trait", "write_recommendation")
    builder.add_edge("write_recommendation", "compile_evaluation")
    builder.add_edge("compile_evaluation", END)
    graph = builder.compile()
    return await graph.ainvoke(EvaluationInputState(job_description=job_description, candidate_context=candidate_context, candidate_full_name=candidate_full_name, key_traits=key_traits, number_of_queries=number_of_queries))
