from typing import Optional
from openai import AzureOpenAI
import os
from dotenv import load_dotenv


def get_azure_openai() -> Optional[AzureOpenAI]:
    load_dotenv()

    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
