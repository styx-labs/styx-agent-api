from typing import Optional, Any, List
from openai import AzureOpenAI
from langchain_openai import AzureChatOpenAI
from langchain_core.language_models import BaseLanguageModel
from services.get_secret import get_secret
from langchain_google_vertexai import VertexAI


openai_4o = AzureChatOpenAI(
    deployment_name="gpt-4o",
    openai_api_version="2024-08-01-preview",
    azure_endpoint=get_secret("azure-openai-endpoint", "2"),
    openai_api_key=get_secret("azure-openai-api-key", "2"),
    temperature=0,
    max_retries=5,
)

openai_4o_mini = AzureChatOpenAI(
    deployment_name="gpt-4o-mini",
    openai_api_version="2024-08-01-preview",
    azure_endpoint=get_secret("azure-openai-endpoint", "2"),
    openai_api_key=get_secret("azure-openai-api-key", "2"),
    temperature=0,
    max_retries=5,
)

gemini_2_flash = VertexAI(
    model="gemini-2.0-flash-001",
)

class LLMWithFallbacks:
    def __init__(self, primary_llm: BaseLanguageModel, fallbacks: List[BaseLanguageModel]):
        self.primary_llm = primary_llm
        self.fallbacks = fallbacks

    def with_structured_output(self, cls):
        return StructuredLLMWithFallbacks(self, cls)

    def invoke(self, *args, **kwargs):
        try:
            return self.primary_llm.invoke(*args, **kwargs)
        except Exception as e:
            for fallback in self.fallbacks:
                try:
                    return fallback.invoke(*args, **kwargs)
                except Exception:
                    continue
            raise e


class StructuredLLMWithFallbacks:
    def __init__(self, llm_with_fallbacks: LLMWithFallbacks, cls: Any):
        self.llm_with_fallbacks = llm_with_fallbacks
        self.cls = cls

    def invoke(self, *args, **kwargs):
        primary = self.llm_with_fallbacks.primary_llm.with_structured_output(self.cls)
        try:
            return primary.invoke(*args, **kwargs)
        except Exception as e:
            for fallback in self.llm_with_fallbacks.fallbacks:
                try:
                    fallback_structured = fallback.with_structured_output(self.cls)
                    return fallback_structured.invoke(*args, **kwargs)
                except Exception:
                    continue
            raise e


llm = LLMWithFallbacks(openai_4o, [gemini_2_flash])
llm_fast = LLMWithFallbacks(openai_4o_mini, [gemini_2_flash])


def get_azure_openai() -> Optional[AzureOpenAI]:
    return AzureOpenAI(
        api_key=get_secret("azure-openai-api-key", "1"),
        api_version="2024-08-01-preview",
        azure_endpoint=get_secret("azure-openai-endpoint", "1"),
    )
