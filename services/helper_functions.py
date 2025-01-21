from langchain_core.messages import HumanMessage, SystemMessage
from services.azure_openai import llm
from langsmith import traceable
from agents.types import KeyTraitsOutput
from agents.prompts import key_traits_prompt, reachout_message_prompt_linkedin, reachout_message_prompt_email
from services.proxycurl import get_linkedin_context


@traceable(name="get_list_of_profiles")
def get_list_of_profiles(ideal_profile_urls: list[str]) -> list[str]:
    if ideal_profile_urls:
        ideal_profiles = []
        for url in ideal_profile_urls:
            _, context, _ = get_linkedin_context(url)
            ideal_profiles.append(context)
        return ideal_profiles
    return []


@traceable(name="get_key_traits")
def get_key_traits(job_description: str, ideal_profiles: list[str]) -> tuple[KeyTraitsOutput, list[str]]:
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
) -> str:
    sections_str = "\n".join(
        [f"{section['section']}: {section['content']} " for section in sections]
    )
    citations_str = "\n".join(
        [f"{citation['distilled_content']}" for citation in citations]
    )
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
                )
            )
        ]
        + [
            HumanMessage(
                content="Write a message to the candidate that is tailored to their profile and the information provided."
            )
        ]
    )
    return output.content
