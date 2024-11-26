from langchain_openai import AzureChatOpenAI
from langchain.agents import create_tool_calling_agent
from langchain.agents import AgentExecutor
from langchain_core.runnables import chain, RunnablePassthrough
import dotenv
import re
import nltk
from nltk.corpus import stopwords
import json
import os
from agents.prompts import agent_prompt, filter_prompt
from services.api import Api
from models import Analysis
from agents.validated_search_tool import ValidatedSearchTool
from langchain_community.tools.tavily_search.tool import TavilySearchResults


class RunSearchChain:
    def run_search(analysis: Analysis):
        nltk.download('stopwords', quiet=True)
        dotenv.load_dotenv()
        llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            temperature=0,
        )

        # search = ValidatedSearchTool()
        search = TavilySearchResults(include_raw_content=True, max_results=5)
        tools = [search]

        agent = create_tool_calling_agent(llm, tools, agent_prompt)
        agent_executor = AgentExecutor(
            agent=agent, tools=tools, return_intermediate_steps=True
        )

        chain = (
            RunnablePassthrough() 
            | {
                "candidates": get_candidates_function,
                "job_description": lambda x: x["job_description"],
                "num_candidates": lambda x: x["num_candidates"],
                "key_traits": lambda x: x["key_traits"]
            }
            | filter_prompt
            | llm
            | (
                lambda x: {
                    "candidates": x.content,
                    "job_description": analysis.job_description,
                    "key_traits": analysis.key_traits
                }
            )
            | agent_executor
        )

        response = chain.invoke({
            "job_description": analysis.job_description,
            "num_candidates": analysis.num_candidates, 
            "school_list": analysis.school_list,
            "location_list": analysis.location_list,
            "graduation_year_upper_bound": analysis.graduation_year_upper_bound,
            "graduation_year_lower_bound": analysis.graduation_year_lower_bound, 
            "key_traits": analysis.key_traits
        })

        return response["output"]


def preprocess_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    stop_words = set(stopwords.words("english"))
    words = text.split()
    words = [word for word in words if word not in stop_words]
    text = ' '.join(words)
    return words


@chain
def get_candidates_function(inputs: dict, multiplier: int=5) -> dict:
    api = Api()
    return api.get_filtered_candidates(preprocess_text(inputs["job_description"]), 
                                       int(inputs["num_candidates"]) * multiplier, 
                                       inputs["school_list"], 
                                       inputs["location_list"], 
                                       inputs["graduation_year_upper_bound"], 
                                       inputs["graduation_year_lower_bound"])
