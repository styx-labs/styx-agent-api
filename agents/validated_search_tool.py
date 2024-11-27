import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from typing import Optional
import os
import requests
from bs4 import BeautifulSoup
from langchain_community.tools.tavily_search.tool import TavilySearchResults
from langchain_core.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel


class WebPageContent(BaseModel):
    url: str
    title: str
    meta_description: str
    body_text: str

    def __str__(self):
        return f"URL: {self.url}\nTitle: {self.title}\nMeta Description: {self.meta_description}\nBody Text: {self.body_text}"


llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0,
)

def clean_text(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower())


def heuristic_validator(
    web_page_content: WebPageContent, candidate_full_name: str
) -> bool:
    cleaned_link_text = clean_text(str(web_page_content))
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


def llm_validator(
    web_page_content: WebPageContent, candidate_full_name: str, candidate_summary: str
) -> bool:
    prompt = PromptTemplate.from_template(
        """
You are validating if a webpage's content is relevant to a specific candidate's profile.

Candidate Full Name: {candidate_full_name}
Candidate Profile: {candidate_summary}

Webpage Content:
{web_page_content}

Please analyze if this webpage is genuinely about the candidate in question. Consider:
1. Does it mention the candidate by name?
2. Does the content align with the candidate's profile?
3. Is this likely to be about a different person with a similar name?

Respond with only "TRUE" if you are confident this webpage is about the correct candidate, or "FALSE" if you are unsure or it's about someone else. 
Response (TRUE/FALSE):
        """
    )

    response = llm.invoke(
        prompt.format(
            candidate_full_name=candidate_full_name,
            candidate_summary=candidate_summary,
            web_page_content=web_page_content,
        )
    )

    cleaned_response = response.content.strip().upper()
    if cleaned_response not in ["TRUE", "FALSE"]:
        logging.error(f"Invalid response from LLM: {cleaned_response}")
        return False

    return cleaned_response == "TRUE"


class ValidatedSearchTool(BaseTool):
    name: str = "validated_search_tool"
    description: str = "Search the web for information about a candidate and validate the results contain their name."
    search_tool: TavilySearchResults = TavilySearchResults(
        include_raw_content=True, max_results=5
    )

    def _fetch_and_validate_url(
        self, url: str, candidate_full_name: str, candidate_summary: str
    ) -> Optional[WebPageContent]:
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()  # Raise an exception for bad status codes

            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string if soup.title else ""
            meta_description = soup.find("meta", attrs={"name": "description"})
            meta_text = meta_description.get("content") if meta_description else ""
            body_text = soup.get_text()

            # Create a WebPageContent object to store the page content
            page_content = WebPageContent(
                url=url,
                title=title,
                meta_description=meta_text,
                body_text=body_text,
            )

            # if llm_validator(page_content, candidate_full_name, candidate_summary):
            if heuristic_validator(page_content, candidate_full_name):
                return page_content
            return None

        except requests.RequestException as e:
            logging.warning(f"Failed to fetch {url}: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error processing {url}: {str(e)}")
            return None

    def _run(
        self, query: str, candidate_full_name: str, candidate_summary: str
    ) -> list[WebPageContent]:
        try:
            raw_results = self.search_tool.invoke({"query": query})

            validated_results = []

            # Fetch and validate URLs in parallel. Create a partial function to pass the candidate_full_name
            fetch_and_validate = partial(
                self._fetch_and_validate_url,
                candidate_full_name=candidate_full_name,
                candidate_summary=candidate_summary,
            )

            # Limit the number of workers to the number of results or 5, whichever is smaller
            with ThreadPoolExecutor(max_workers=min(5, len(raw_results))) as executor:
                future_to_url = {
                    executor.submit(fetch_and_validate, result.get("url")): result.get(
                        "url"
                    )
                    for result in raw_results
                }
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        page_content = future.result()
                        if page_content:
                            validated_results.append(page_content)
                    except Exception as e:
                        logging.error(f"Error processing {url}: {str(e)}")

        except Exception as e:
            logging.error(f"Unexpected error in _run: {str(e)}")
            return []

        return validated_results

    def _arun(self, query: str, candidate_full_name: str) -> list[WebPageContent]:
        raise NotImplementedError("This tool does not support async execution.")
    