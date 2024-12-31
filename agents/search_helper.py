import re
import requests
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage
from services.azure_openai import llm

report_planner_query_writer_instructions = """ 
You are an expert at researching people online. Your goal is to find detailed information about a candidate for a job opportunity.
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


def clean_text(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower())


def heuristic_validator(content, title, candidate_full_name: str) -> bool:
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
    confidence: float


async def llm_validator(
    raw_content, candidate_full_name: str, candidate_context: str
) -> LLMValidatorOutput:
    prompt = """
You are a validator determining if a webpage's content is genuinely about a specific candidate.

Candidate Full Name: {candidate_full_name}
Candidate Profile:
{candidate_context}

Raw Content: {raw_content}

Use the following guidelines to validate if this webpage is about the candidate in question:
1. **Name Match**:
   - The webpage must explicitly mention the candidate's full name or a clear variation.

2. **Context Alignment**:
   - Current or past employers mentioned in the candidate's profile.
   - Educational institutions from the candidate's background.
   - Job titles or roles from the candidate's experience.
   - Projects or achievements mentioned in the candidate's profile.
   - Time periods that align with the candidate's career history.

3. **Confidence Check**:
   - Is there any conflicting information that suggests this might be about a different person?
   - Are there enough specific details to be confident this is about our candidate?
   - Could this content reasonably apply to someone else with the same name?

While you should be very careful in your evaluation, we don't want to reject a valid source. As long as you have reasonable confidence that this is about the candidate in question, you should return `True`.

**Additionally**, provide a confidence score between `0` and `1` indicating how confident you are in your validation.
    """

    structured_llm = llm.with_structured_output(LLMValidatorOutput)
    output = structured_llm.invoke(
        [
            SystemMessage(
                content=prompt.format(
                    candidate_full_name=candidate_full_name,
                    candidate_context=candidate_context,
                    raw_content=raw_content,
                )
            )
        ]
        + [
            HumanMessage(
                content="Validate if this webpage is about the candidate in question."
            )
        ]
    )
    return output


async def distill_source(raw_content, candidate_full_name: str):
    prompt = """
        You will be given a string of raw content from a webpage.
        Please extract the relevant information about the given person from the raw HTML.
        Describe what the source is, what it is about, and how it is relevant to the person, etc.
        Write your response in paragraph form.

        Here is the raw content:
        {raw_content}

        Here is the person's full name:
        {candidate_full_name}
    """

    output = llm.invoke(
        [
            SystemMessage(
                content=prompt.format(
                    raw_content=raw_content, candidate_full_name=candidate_full_name
                )
            )
        ]
        + [
            HumanMessage(
                content="Extract the relevant information about the given person from the raw HTML."
            )
        ]
    )
    return output.content


async def deduplicate_and_format_sources(
    search_response,
    max_tokens_per_source,
    candidate_full_name: str,
    candidate_context: str,
):
    """
    Takes either a single search response or list of responses from Tavily API and formats them.
    Limits the raw_content to approximately max_tokens_per_source.

    Args:
        search_response: Either:
            - A dict with a 'results' key containing a list of search results
            - A list of dicts, each containing search results

    Returns:
        tuple:
            - str: Formatted string with deduplicated and ranked sources
            - list[dict]: List of citations with URLs and confidence scores
    """
    # Convert input to list of results
    if isinstance(search_response, dict):
        sources_list = search_response["results"]
    elif isinstance(search_response, list):
        sources_list = []
        for response in search_response:
            if isinstance(response, dict) and "results" in response:
                sources_list.extend(response["results"])
            else:
                sources_list.extend(response)
    else:
        raise ValueError(
            "Input must be either a dict with 'results' or a list of search results"
        )

    # Deduplicate by URL
    unique_sources = {}
    for source in sources_list:
        if source["url"] not in unique_sources:
            unique_sources[source["url"]] = source

    # Create a list of URLs to remove
    urls_to_remove = []
    for source in unique_sources.values():
        try:
            result = requests.get(source["url"], timeout=5)
            content = result.text
            char_limit = max_tokens_per_source * 4
            source["raw_content"] = (
                content[:char_limit] if len(content) > char_limit else content
            )
        except Exception:
            print(f"Error fetching {source['url']}")
            urls_to_remove.append(source["url"])
            continue

    # Remove failed URLs after iteration
    for url in urls_to_remove:
        del unique_sources[url]

    valid_sources = {}
    citations = []
    # Validate sources and assign confidence scores
    for source in unique_sources.values():
        if heuristic_validator(source["content"], source["title"], candidate_full_name):
            llm_output = await llm_validator(
                source["raw_content"], candidate_full_name, candidate_context
            )
            if llm_output.confidence > 0.5:
                valid_sources[source["url"]] = {
                    "source": source,
                    "confidence": llm_output.confidence,
                }

    # Rank sources by confidence descending
    ranked_sources = sorted(
        valid_sources.values(), key=lambda x: x["confidence"], reverse=True
    )

    # Assign weights based on confidence
    for source_info in ranked_sources:
        source = source_info["source"]
        source["weight"] = source_info["confidence"]

    # Distill sources with weights
    for source_info in ranked_sources:
        source = source_info["source"]
        source["distilled_content"] = await distill_source(
            source["raw_content"], candidate_full_name
        )

    # Format output
    formatted_text = "Sources:\n\n"
    citation_list = []
    for i, source_info in enumerate(ranked_sources, 1):
        source = source_info["source"]
        formatted_text += f"[{i}]: {source['title']}:\n"
        formatted_text += f"URL: {source['url']}\n"
        formatted_text += f"Relevant content from source: {source['distilled_content']} (Confidence: {source_info['confidence']})\n===\n"

        citation_list.append(
            {"index": i, "url": source["url"], "confidence": source_info["confidence"]}
        )

    return formatted_text.strip(), citation_list
