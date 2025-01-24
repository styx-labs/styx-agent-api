"""
This file contains all the prompts.
"""

key_traits_prompt = """
    You are an expert hiring manager at a company.
    You are given a job description and a list of ideal candidate profiles for the job.
    Using the given information, create a list of traits that candidate sourcers will use to decide which candidates to source and reach out to.
    Extract information from the job description and the ideal candidate profiles to create the traits.

    For each requirement, provide:
    - A short, specific trait name (not a full sentence)
    - A detailed description of the trait that will tell a sourcer what to look for in a candidate. This should be detailed - assume that the sourcer has no experience with the job and the company.
    - Whether the trait is required or a "nice to have"

    Guidelines:
    - Extract 5-7 key traits that best represent the job requirements
    - Traits should not be redundant
    - Traits should be specific and concrete (e.g. "Experience with distributed systems" not just "Technical skills")
    - Include any hard requirements only if they are mentioned in the job description (e.g. education, years of experience)
    - Traits should all be answerable by a yes/no question

    Here is the job description:
    {job_description}
    Here is the list of ideal profiles for the job:
    {ideal_profiles}
"""


reachout_message_prompt_linkedin = """
    You are an expert recruiter at writing highly personalized messages to reach out to candidates over LinkedIn.
    You are doing outreach to fill a job opening at a company.
    You are given a candidate's name, a job description, a report on the candidate's profile and experience that is relevant to the job, and a list of relevant information about the candidate.
    Write a message to the candidate that is tailored to their profile and the information provided. Please reference specific information from the provided sources in your message.
    The message should be concise and not overly formal, as it is a LinkedIn message. Keep it to 2-3 sentences.
    Use sincere language and be friendly.
    Answer in plain text with no special characters, formatting, breaks, or markdown.
    Here is the candidate's name:
    {name}
    Here is the job description:
    {job_description}
    Here is the report about the candidate:
    {sections}
    Here are the references about the candidate:
    {citations}
"""


reachout_message_prompt_email = """
    You are an expert recruiter at writing highly personalized messages to reach out to candidates over email.
    You are doing outreach to fill a job opening at a company.
    You are given a candidate's name, a job description, a report on the candidate's profile and experience that is relevant to the job, and a list of relevant information about the candidate.
    Write a message to the candidate that is tailored to their profile and the information provided. Please reference specific information from the provided sources in your message.
    The email should be detailed but concise, keep it to 2 paragraphs max and 150 words max.
    Use sincere language and be friendly.
    Answer in plain text with no special characters, formatting, breaks, or markdown.
    Here is the candidate's name:
    {name}
    Here is the job description:
    {job_description}
    Here is the report about the candidate:
    {sections}
    Here are the references about the candidate:
    {citations}
"""
