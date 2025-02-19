from langchain_core.messages import HumanMessage, SystemMessage
from services.llms import llm
from langsmith import traceable
from agents.prompts import (
    key_traits_prompt,
    reachout_message_prompt_linkedin,
    reachout_message_prompt_email,
    headless_evaluate_prompt,
    edit_key_traits_prompt,
    edit_job_description_prompt,
)

from agents.linkedin_processor import get_linkedin_profile_with_companies
from services.firestore import get_user_templates
from models.evaluation import KeyTraitsOutput, HeadlessEvaluationOutput, EditKeyTraitsOutput, EditJobDescriptionOutput
from models.jobs import CalibratedProfiles


@traceable(name="headless_evaluate_helper")
def headless_evaluate_helper(
    candidate_name: str, 
    candidate_context: str, 
    job_description: str, 
    calibrations: list[dict] = None
) -> HeadlessEvaluationOutput:
    if calibrations:
        calibrations_str = """
            ===============================================\n
            Reference Evaluations:\n
            The following sections have examples of candidates who have been pre-evaluated by the hiring manager. Use these as benchmarks to calibrate your evaluation.\n
            ===============================================\n
        """

        good_fit_profiles = [calibration for calibration in calibrations if calibration['calibration_result'] == 'GOOD_FIT']
        if good_fit_profiles:
            calibrations_str += "Here are profiles of candidates who are a good fit for the job, and should score 3-4:\n"
            for i, profile in enumerate(good_fit_profiles):
                calibrations_str += f"Profile {i+1}:\n"
                calibrations_str += f"{profile['candidate_context']}\n"
                calibrations_str += "----------------------------------------\n"
            calibrations_str += "==============================================\n"
        
        neutral_fit_profiles = [calibration for calibration in calibrations if calibration['calibration_result'] == 'MAYBE']
        if neutral_fit_profiles:
            calibrations_str += "Here are profiles of candidates who are potential fits for the job, and should score 2:\n"
            for i, profile in enumerate(neutral_fit_profiles):
                calibrations_str += f"Profile {i+1}:\n"
                calibrations_str += f"{profile['candidate_context']}\n"
                calibrations_str += "----------------------------------------\n"
            calibrations_str += "==============================================\n"

        bad_fit_profiles = [calibration for calibration in calibrations if calibration['calibration_result'] == 'BAD_FIT']
        if bad_fit_profiles:
            calibrations_str += "Here are profiles of candidates who are not a good fit for the job, and should score 0-1:\n"
            for i, profile in enumerate(bad_fit_profiles):
                calibrations_str += f"Profile {i+1}:\n"
                calibrations_str += f"{profile['candidate_context']}\n"
                calibrations_str += "----------------------------------------\n"
            calibrations_str += "==============================================\n"
    else:
        calibrations_str = ""
    
    structured_llm = llm.with_structured_output(HeadlessEvaluationOutput)
    output = structured_llm.invoke(
        [
            SystemMessage(
                content=headless_evaluate_prompt.format(
                    candidate_name=candidate_name,
                    candidate_context=candidate_context,
                    job_description=job_description, 
                    calibrations=calibrations_str
                )
            ),
            HumanMessage("Evaluate the candidate based on the job description and calibrations."),
        ]
    )
    return output


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


@traceable(name="edit_key_traits_llm")
def edit_key_traits_llm_helper(key_traits: dict, prompt: str) -> EditKeyTraitsOutput:
    key_traits_str = "\n".join(
        [
            f"trait: {trait['trait']}\ndescription: {trait['description']}\nrequired: {trait['required']}"
            for trait in key_traits
        ]
    )
    structured_llm = llm.with_structured_output(EditKeyTraitsOutput)
    output = structured_llm.invoke(
        [
            SystemMessage(
                content=edit_key_traits_prompt.format(
                    key_traits=key_traits_str, prompt=prompt
                )
            ),
            HumanMessage(content="Edit the key traits to meet the user's requirements."),
        ]
    )
    return output


@traceable(name="edit_job_description_llm")
def edit_job_description_llm_helper(
    job_description: str, prompt: str
) -> EditJobDescriptionOutput:
    structured_llm = llm.with_structured_output(EditJobDescriptionOutput)
    output = structured_llm.invoke(
        [
            SystemMessage(content=edit_job_description_prompt.format(job_description=job_description, prompt=prompt)),
            HumanMessage(content="Edit the job description to meet the user's requirements."),
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
