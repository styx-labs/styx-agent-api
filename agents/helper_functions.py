from langchain_core.messages import HumanMessage, SystemMessage
from services.azure_openai import llm
from langsmith import traceable
from agents.prompts import (
    key_traits_prompt,
    reachout_message_prompt_linkedin,
    reachout_message_prompt_email,
)
from agents.linkedin_processor import get_linkedin_profile_with_companies
from services.firestore import get_user_templates
from typing import List
import services.firestore as firestore
from models.evaluation import KeyTraitsOutput


@traceable(name="get_list_of_profiles")
async def get_list_of_profiles(ideal_profile_urls: list[str]) -> list[str]:
    if ideal_profile_urls:
        ideal_profiles = []
        for url in ideal_profile_urls:
            _, profile, _ = await get_linkedin_profile_with_companies(url)
            ideal_profiles.append(profile.to_context_string())
        return ideal_profiles
    return []


@traceable(name="get_key_traits")
def get_key_traits(
    job_description: str, ideal_profiles: list[str]
) -> tuple[KeyTraitsOutput, list[str]]:
    if ideal_profiles:
        ideal_profiles_str = ""
        for profile in ideal_profiles:
            ideal_profiles_str += profile
            ideal_profiles_str += "\n---------\n---------\n"
    else:
        ideal_profiles_str = ""

    structured_llm = llm.with_structured_output(KeyTraitsOutput)
    output = structured_llm.invoke(
        [
            SystemMessage(
                content=key_traits_prompt.format(
                    job_description=job_description, ideal_profiles=ideal_profiles_str
                )
            ),
            HumanMessage(
                content="Generate a list of key traits relevant to the job description."
            ),
        ]
    )
    return output


@traceable(name="get_reachout_message")
def get_reachout_message(
    name: str,
    job_description: str,
    sections: list[dict],
    citations: list[dict],
    format: str,
    user_id: str = None,
    template_content: str = None,
) -> str:
    sections_str = "\n".join(
        [f"{section['section']}: {section['content']} " for section in sections]
    )
    citations_str = "\n".join(
        [f"{citation['distilled_content']}" for citation in citations]
    )

    # Use provided test template if available, otherwise get user's templates
    if template_content:
        template = template_content
    else:
        template = "No template provided - use default professional recruiting style."
        if user_id:
            templates = get_user_templates(user_id)
            if format == "linkedin":
                template = templates.linkedin_template or template
            else:
                template = templates.email_template or template

    # Use default prompt based on format
    prompt = (
        reachout_message_prompt_linkedin
        if format == "linkedin"
        else reachout_message_prompt_email
    )

    output = llm.invoke(
        [
            SystemMessage(
                content=prompt.format(
                    name=name,
                    job_description=job_description,
                    sections=sections_str,
                    citations=citations_str,
                    template=template,
                )
            ),
            HumanMessage(
                content="Generate a message that strictly follows the provided template structure and style, while personalizing the specific details for this candidate. Make sure to include all key elements from the template."
            ),
        ]
    )
    return output.content
