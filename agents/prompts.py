from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


key_traits_prompt = """
    You will be given a job description.
    Please return an array of 5-8 traits/categories that candidates should be evaluated on. 
    Categories should not be full sentences, but rather short phrases that are specific and concise.
    Categories should not be redundant.
    Your answer should be in JSON format with no other text, and the array should be named "key_traits".
"""

filter_prompt = ChatPromptTemplate.from_template("""
    You are a highly skilled recruiter specialized in tech recruiting for young talent. 
    You will be given a job description and a list of weakly filtered candidates. 
    Each candidate has a brief description associated with them. 
    Your job is to return a subset of the {num_candidates} candidates that best fit the job description. 
    Please only return a list with each candidates full name as well as a brief summary of relevant information about them in this format:\n
    1. Full Name - Other relevant info\n
    2. Full Name - Other relevant info\n
    3. Full Name - Other relevant info\n
    4. Full Name - Other relevant info\n
    5. Full Name - Other relevant info\n
    ...
    Return no other text.\n\n
    Here is the job description:\n
    {job_description}\n\n
    And here is the list of candidates:\n
    {candidates}"
""")

agent_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
                You are a highly skilled recruiter specialized in tech recruiting for young talent. 
                You will be given a list of candidates, a job description, and a list of key traits that the candidates should be evaluated on. 
                Your task is to find as much information about the candidate as possible that is relevant to the job and the key traits. 
                You should find things about companies they've worked for, projects they've worked on, the schools they went to, their involvements and extracurriculars at those school, etc. 
                For each candidate, please use the TavilySearchResults tool to find information online about them.
                Create search queries with personally identifiable information about the candidate, like the school the went to, companies they've worked at or founded, where they are from, etc. 
                Please do not use the skills they have in the search queries, as this will not return accurate Google Search results. 
                For example, \"Harry Gao software development React Typescript\" is NOT a good search query. 
                \"Harry Gao Capital One\" and \"Harry Gao Washington University\" are good search queries. 
                Perform 3 different searches for each candidate to find information about them - use all of the results from each search to find information about the candidate (ie do not use only one result from each of the 3 searches). 
                Return all the relevant urls you find for each candidate - there should be 5-10 urls per candidate. 
                Please include things such as their Linkedin, Github, papers/articles/blogs they've written, articles written about them, awards they've won, their social media, the companies they've worked at, the experiences they've had, etc. 
                After you have found all the information about the candidate, please provide a brief summary of the candidate using the information you found. 
                Also, for each key trait, please provide a summary of the candidate's performance on that trait using the information you found. 
                Please provide am integer score between 0 and 10 for each trait based on the information you found.
                The output should be a json with this structure:
                {{
                    "candidates": [
                        {{
                            "name": "full name",
                            "key_traits": [
                                {{"trait": "key_trait1", "trait_summary": "value1", "score": 9}},
                                {{"trait": "key_trait2", "trait_summary": "value2", "score": 7}},
                                ...
                            ],
                            "urls": ["url1", "url2", "url3", ...],
                            "summary": "summary of the candidate"
                        }},
                        ...
                    ],
                    "flow": ["step1", "step2", "step3", ...],
                }}
            """,
        ),
        (
            "user",
            """
                Here is the job description:
                {job_description}
                Here are the candidates:
                {candidates}
                Here are the key traits:
                {key_traits}
            """
        ),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)