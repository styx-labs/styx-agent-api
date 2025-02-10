from langchain_core.messages import HumanMessage, SystemMessage
from services.llms import llm
from langsmith import traceable
from agents.prompts import (
    key_traits_prompt,
    reachout_message_prompt_linkedin,
    reachout_message_prompt_email,
)

from agents.linkedin_processor import get_linkedin_profile_with_companies
from services.firestore import get_user_templates
from models.evaluation import KeyTraitsOutput
from models.base import CalibratedProfiles


@traceable(name="get_calibrated_profiles_linkedin")
def get_calibrated_profiles_linkedin(
    calibrated_profiles: list[CalibratedProfiles],
) -> list[CalibratedProfiles]:
    if calibrated_profiles:
        for calibrated_profile in calibrated_profiles:
            _, profile, _ = get_linkedin_profile_with_companies(calibrated_profile.url)
            calibrated_profile.profile = profile
    return calibrated_profiles


@traceable(name="get_key_traits")
def get_key_traits(
    job_description: str, calibrated_profiles: list[CalibratedProfiles]
) -> tuple[KeyTraitsOutput, list[str]]:
    if calibrated_profiles:
        calibrate_profiles_str = ""
        for calibrated_profile in calibrated_profiles:
            calibrate_profiles_str += str(calibrated_profile)
            calibrate_profiles_str += "\n---------\n---------\n"
    else:
        calibrate_profiles_str = ""

    structured_llm = llm.with_structured_output(KeyTraitsOutput)
    output = structured_llm.invoke(
        [
            SystemMessage(
                content=key_traits_prompt.format(
                    job_description=job_description,
                    calibrated_profiles=calibrate_profiles_str,
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
