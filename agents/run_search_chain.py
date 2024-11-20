from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_tool_calling_agent
from langchain.agents import AgentExecutor
from langchain_core.runnables import chain
import dotenv
import re
import requests
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import json
import os
from langchain_core.runnables import RunnablePassthrough
from agents.prompts import agent_prompt, filter_prompt


class RunSearchChain:
    def run_search(job_description: str, num_candidates: str):
        nltk.download('stopwords', quiet=True)
        dotenv.load_dotenv()
        llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            temperature=0,
        )

        search = TavilySearchResults(include_raw_content=True, max_results=5)
        tools = [search]

        agent = create_tool_calling_agent(llm, tools, agent_prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, return_intermediate_steps=True)

        chain = (
            {
                "candidates": get_candidates_function,
                "job_description": RunnablePassthrough().pick("job_description"),
                "num_candidates": RunnablePassthrough().pick("num_candidates")
            }
            | filter_prompt
            | llm
            | (lambda x: {"candidates": x.content, "job_description": RunnablePassthrough().pick("job_description"), "num_candidates": RunnablePassthrough().pick("num_candidates")})
            | agent_executor
        )

        response = chain.invoke({
            "job_description": job_description,
            "num_candidates": num_candidates
        })

        return response["output"]

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    stop_words = set(stopwords.words('english'))
    words = text.split()
    words = [word for word in words if word not in stop_words]
    text = ' '.join(words)
    stemmer = PorterStemmer()
    words = text.split()
    words = [stemmer.stem(word) for word in words]
    return words

@chain
def get_candidates_function(inputs: dict, multiplier: int=5) -> dict:
    url = "https://vector-search-db-16250094868.us-central1.run.app/?description="
    job_description = preprocess_text(inputs["job_description"])
    for i, word in enumerate(job_description):
        url += word
        if i < len(job_description) - 1:
            url += "+"
    url += "&num_candidates=" + str(int(inputs["num_candidates"]) * multiplier)
    response = requests.get(url)
    if response.status_code == 200:
        content = response.text
        content = json.loads(content)
        return content
    else:
        print(f"Error: {response.status_code}")
        return None
