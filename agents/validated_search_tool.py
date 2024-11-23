from langchain_core.tools import BaseTool
from langchain_community.tools.tavily_search.tool import TavilySearchResults
import requests
from bs4 import BeautifulSoup
from pydantic import Field
import re


def clean_text(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower())


def heuristic_validator(link_text: str, candidate_full_name: str):
    cleaned_link_text = clean_text(link_text)
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


class ValidatedSearchTool(BaseTool):
    name = "validated_search_tool"
    description = "Search the web for information about a candidate and validate the results contain their name."
    search_tool: TavilySearchResults = Field(
        default_factory=lambda: TavilySearchResults(
            include_raw_content=True, max_results=5
        )
    )

    def __init__(self):
        super().__init__()
        self.search_tool = TavilySearchResults(include_raw_content=True, max_results=5)

    def _fetch_and_validate_url(self, url: str, candidate_full_name: str) -> bool:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                title = soup.title.string if soup.title else ""
                meta_description = soup.find("meta", attrs={"name": "description"})
                meta_text = meta_description.get("content") if meta_description else ""
                body_text = soup.get_text()
                return heuristic_validator(
                    title + meta_text + body_text, candidate_full_name
                )
            return False
        except Exception as e:
            print(e)
            return False

    def _run(self, query: str, candidate_full_name: str) -> list:
        raw_results = self.search_tool.invoke({"query": query})
        validated_results = []
        for result in raw_results:
            if self._fetch_and_validate_url(result["url"], candidate_full_name):
                validated_results.append(result)
        return validated_results

    def _arun(self, query: str, candidate_full_name: str) -> list:
        raise NotImplementedError("This tool does not support async execution.")
