from typing import Optional
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI


load_dotenv()

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0,
)


def get_azure_openai() -> Optional[AzureOpenAI]:
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
