"""
This file contains all the prompts.
"""


key_traits_prompt = """
    You will be given a job description.
    Please return an array of 3-5 traits/categories that candidates should be evaluated on. 
    Categories should not be full sentences, but rather short phrases that are specific and concise.
    Categories should not be redundant.

    Here is the job description:
    {job_description}
"""


search_query_prompt = """ 
    You are an expert at researching people online. Your goal is to find detailed information about a candidate for a job opportunity.
    The candidate is:
    {candidate_full_name}
    {candidate_context}
    The job they're being considered for is:
    {job_description}
    Generate {number_of_queries} search queries that will help gather comprehensive information about this candidate. 
    Guidelines for creating effective person-focused queries:
    1. Create simple, direct queries using key identifying information
    2. Avoid complex queries with multiple keywords or technical terms
    3. Focus on finding the candidate's digital presence
    4. Include queries that might surface profiles, articles, or mentions from:
    - Professional organizations and news
    - University publications
    - Personal blogs
    - GitHug repositories
    Make each query specific and focused on one aspect of the candidate's background.
"""


validation_prompt = """
    You are a validator determining if a webpage's content is genuinely about a specific candidate.

    Candidate Full Name: {candidate_full_name}
    Candidate Profile:
    {candidate_context}
    Raw Content: {raw_content}

    Use the following guidelines to validate if this webpage is about the candidate in question:
    1. **Name Match**:
    - The webpage must explicitly mention the candidate's full name or a clear variation.

    2. **Context Alignment**:
    - Current or past employers mentioned in the candidate's profile.
    - Educational institutions from the candidate's background.
    - Job titles or roles from the candidate's experience.
    - Projects or achievements mentioned in the candidate's profile.
    - Time periods that align with the candidate's career history.

    3. **Confidence Check**:
    - Is there any conflicting information that suggests this might be about a different person?
    - Are there enough specific details to be confident this is about our candidate?
    - Could this content reasonably apply to someone else with the same name?

    While you should be very careful in your evaluation, we don't want to reject a valid source. Provide a confidence score between `0` and `1`, with anything above `0.5` being a valid source.
"""


distill_source_prompt = """
    You will be given a string of raw content from a webpage.
    Please extract the relevant information about the given person from the raw HTML.
    Describe what the source is, what it is about, and how it is relevant to the person, etc.
    Write your response in paragraph form.

    Limit the response to 150 words.

    Here is the raw content:
    {raw_content}

    Here is the person's full name:
    {candidate_full_name}
"""


recommendation_prompt = """
    You are an expert at evaluating candidates for a job.
    You are given a specific job description and a report evaluating specific areas of the candidate.
    Write a recommendation on how good of a fit the candidate is for the job that is based on the information provided.
    This should be a short 2-3 sentence evaluation on how well the candidate fits the job description based on the information provided.
    Here is the job description:
    {job_description}
    Here is the candidate's name:
    {candidate_full_name}
    Here is the report about the candidate:
    {completed_sections}

    When you mention information that you get from a source, please include a citation in your evaluation by citing the number of the source that links to the url in a clickable markdown format.
    For example, if you use information from sources 3 and 7, cite them like this: [3](url), [7](url). 
    Don't include a citation if you are not referencing a source.
"""


trait_evaluation_prompt = """
    You are an expert at evaluating candidates for a job.
    You are given a specific trait that you are evaluating the candidate on.
    You are also given a string of sources that contain information about the candidate.
    Write a evaluation of the candidate in this specific trait based on the provided information.
    It is possible that there is no information about the candidate in this trait - if this is the case, please mention that no information was found regarding the trait, not that the candidate does not have the trait.

    Output two values:
    - An integer score from 0 to 10 that rates the candidate based on their experience in this trait.
    - A string of text that is the evaluation of the candidate in this specific trait based on the provided information. This should be a no more than 100 words.

    In the string of text, when you mention information that you get from a source, please include a citation in your evaluation by citing the number of the source that links to the url in a clickable markdown format.
    For example, if you use information from sources 3 and 7, cite them like this: [3](url), [7](url). 
    Don't include a citation if you are not referencing a source.
    Cite sources liberally.

    Here is the trait you are evaluating the candidate on:
    {section}
    Here is the candidate's name:
    {candidate_full_name}
    Here is the candidate's basic profile:
    {candidate_context}
    Here are the sources about the candidate:
    {source_str}
"""


reachout_message_prompt = """
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
