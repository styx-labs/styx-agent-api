from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


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
                You will be given a list of candidates and a job description. 
                Your task is to find as much information about the candidate as possible that is relevant to the job. 
                You should find things about companies they've worked for, projects they've worked on, the schools they went to, their involvements and extracurriculars at those school, etc. 
                For each candidate, please use the tools available to you to to find this information.
            """,
        ),
        (
            "user",
            """
                Here is a list of {num_candidates} candidates and a job description. 
                Please find relevant information about each candidate with the tools available to you. 
                You have access to a Google Search API tool. 
                Please use it to find additional information on each candidate. 
                Create search queries with personally identifiable information about the candidate, like the school the went to, companies they've worked at or founded, where they are from, etc. 
                Please do not use the skills they have in the search queries, as this will not return accurate Google Search results. 
                For example, \"Harry Gao software development React Typescript\" is NOT a good search query. 
                \"Harry Gao Capital One\" and \"Harry Gao Washington University\" are good search queries. 
                Perform 3 different searches for each candidate to find information about them - use all of the results from each search to find information about the candidate (ie do not use only one result from each of the 3 searches). 
                Return all the relevant urls you find for each candidate - there should be 5-10 urls per candidate. 
                Please include things such as their Linkedin, Github, papers/articles/blogs they've written, articles written about them, awards they've won, their social media, the companies they've worked at, the experiences they've had, etc. 
                Finally, create a summary that describes everything you know and found about the candidate, and why they are a good fit for the role. Please go in depth about the candidate's experiences, background, skills, etc. Please talk about everything you found online about each candidate and how it relates to the role. Please be very detailed in your investigation.
                \n\nHere is the job description:
                \n{job_description}\n\n
                Here are the candidates:
                \n{candidates}\n\n
                Please output the results in JSON valid format with no extra text. 
                Each candidate in the output should have a name, summary, and relevant urls field that is an array of URL strings.\n\n
                Here is an example of the type of output we are looking for each candidate (the summary is an example - in reality you should go more in depth):
                \n    \"name\": \"Harry Gao\",
                \n    \"summary\": \"Harry Gao is a senior studying computer science + math student at Washington University in St. Louis. He has interned as a Software Engineer at Capital One and a Data scientist at UnitedHealth Group. These are both Fortune 500 companies. Capital One is reputable in the tech world for being early to adopt AI and cloud services. From his Github, he is proficient in Python, React, and Pytorch. He has 2 published papers on deep learning for image restoration and image compression. He has worked at a startup called Mozi and is also currently founding a startup called UniLink that specializes in talent discovery for headhunters - he was a finalist in the 2024 Skandalaris Venture Competition. He is passionate about software, machine learning, and the startup space. With a passion for software development, machine learning, and the startup ecosystem, Harry is an ideal candidate for the founding engineer position at Mercor. His expertise in AI, combined with his software engineering and design abilities, positions him well for the technical demands of the role. Moreover, his entrepreneurial experience as a founder equips him with critical skills in leadership, innovation, and strategic thinking, which would enable him to make a significant impact at Mercor.\"\n    
                \"relevant_urls\": [
                \n        \"https://www.linkedin.com/in/harrygao56/\",
                \n        \"https://github.com/harrygao56\",
                \n        \"https://scholar.google.com/citations?user=WK_bR0gAAAAJ&hl=en&inst=2230987035966559800\",
                \n        \"https://scholar.google.com/citations?user=WK_bR0gAAAAJ&hl=en&inst=2230987035966559800\",
                \n        \"https://sts.wustl.edu/people/harry-gao/\",
                \n        \"https://skandalaris.wustl.edu/blog/2024/10/23/fall-2024-skandalaris-venture-competition-finalists-announced/\",
                \n]

                In addition, please also include a field in the output detailing the flow you took to find the information about the candidates.
                The flow field should be a list of strings, each string representing a step you took in your investigation, including the search queries you used, the urls you followed, etc. Please be specific and detailed but brief. 
                The final output should be a JSON object with the following fields:
                - candidates
                - flow
                """
        ),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)