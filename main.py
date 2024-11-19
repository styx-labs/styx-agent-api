from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, engine
import models
import json
from langflow.load import run_flow_from_json


agent_system_prompt = """
You are a highly skilled recruiter specialized in tech recruiting for young talent. 
You will be given a list of candidates and a job description. 
Your task is to find as much information about the candidate as possible that is relevant to the job. 
You should find things about companies they've worked for, projects they've worked on, the schools they went to, their involvements and extracurriculars at those school, etc. 
For each candidate, please use the tools available to you to to find this information.
"""

agent_user_prompt = """
Here is a list of {n} candidates and a job description. 
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
\n{description}\n\n
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

filter_prompt = """
You are a highly skilled recruiter specialized in tech recruiting for young talent. 
You will be given a job description and a list of weakly filtered candidates. 
Each candidate has a brief description associated with them. 
Your job is to return a subset of the {n} candidates that best fit the job description. 
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
"""

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class JobDescription(BaseModel):
    description: str
    num_candidates: int


def analyze_job_description(description: str, num: int) -> str:
    # Mock result that matches the expected JSON structure
    mock_result = {
        "candidates": [
            {
                "name": "Jane Smith",
                "summary": "Jane Smith is a senior Computer Science student at MIT with extensive experience in machine learning and software development. She completed internships at Google and Microsoft, where she worked on large-scale distributed systems. She has published research on natural language processing and maintains several popular open-source projects. Her technical expertise combined with leadership experience as president of MIT's AI Club makes her an excellent candidate.",
                "relevant_urls": [
                    "https://www.linkedin.com/in/janesmith",
                    "https://github.com/janesmith",
                    "https://scholar.google.com/citations?user=JS123",
                    "https://mit.edu/~jsmith/research",
                    "https://medium.com/@janesmith",
                ],
            },
            {
                "name": "John Doe",
                "summary": "John Doe is a recent graduate from Stanford University with a focus on distributed systems and cloud computing. He has built several successful tech startups and has experience scaling applications on AWS. His projects have been featured in TechCrunch and he was a finalist in Y Combinator's Summer 2023 batch.",
                "relevant_urls": [
                    "https://www.linkedin.com/in/johndoe",
                    "https://github.com/johndoe",
                    "https://techcrunch.com/2023/startup-feature",
                    "https://stanford.edu/projects/cloud-computing",
                    "https://medium.com/@johndoe",
                ],
            },
        ],
        "flow": [
            "Searched 'Jane Smith MIT AI research'",
            "Found LinkedIn profile and GitHub repositories",
            "Discovered published papers on Google Scholar",
            "Searched 'John Doe Stanford startup'",
            "Found TechCrunch article and Y Combinator profile",
            "Analyzed GitHub contributions and technical blog posts",
        ],
    }

    return json.dumps(mock_result)


# def analyze_job_description(description: str, num: int) -> str:
#     TWEAKS = {
#         "SearchAPI-8xIft": {
#             "api_key": "Spzu9Rgz6wM7yg9DoHewo91p",
#             "engine": "google",
#             "input_value": "",
#             "max_results": 5,
#             "max_snippet_length": 100,
#             "search_params": {},
#         },
#         "url_content_fetcher-bDGCl": {"fetch_params": {}, "url": ""},
#         "ToolCallingAgent-5Q0Er": {
#             "handle_parsing_errors": True,
#             "input_value": "",
#             "max_iterations": 15,
#             "system_prompt": agent_system_prompt,
#             "user_prompt": "{input}",
#             "verbose": True,
#         },
#         "CustomComponent-W7bsk": {"input_value": ""},
#         "URL-YhNkF": {"format": "Text", "urls": ""},
#         "Prompt-W93bF": {
#             "template": filter_prompt,
#             "candidates": "",
#             "job_description": "",
#             "n": "",
#         },
#         "TextInput-Mijxy": {"input_value": str(num)},
#         "TextInput-JyTyM": {"input_value": description},
#         "AzureOpenAIModel-rRgMw": {
#             "api_key": "d26cf6f9ccd34426b28079b675ac40f9",
#             "api_version": "2023-03-15-preview",
#             "azure_deployment": "gpt-4o-mini",
#             "azure_endpoint": "https://unilink-gpt.openai.azure.com/",
#             "input_value": "",
#             "max_tokens": None,
#             "stream": False,
#             "system_message": "",
#             "temperature": 0.7,
#         },
#         "Prompt-sLi4Q": {
#             "template": agent_user_prompt,
#             "candidates": "",
#             "n": "",
#             "description": "",
#         },
#         "TextOutput-jhX8N": {"input_value": ""},
#     }
#     result = (
#         run_flow_from_json(
#             flow="unlink-agent.json",
#             input_value="message",
#             # session_id="",  # provide a session id if you want to use session state
#             fallback_to_env_vars=True,  # False by default
#             tweaks=TWEAKS,
#         )[0]
#         .outputs[0]
#         .results["text"]
#         .data["text"]
#     )

#     # Trim characters from start until we find opening brace
#     while result and not result.startswith("{"):
#         result = result[1:]

#     # Trim characters from end until we find closing brace
#     while result and not result.endswith("}"):
#         result = result[:-1]

#     return result


@app.post("/analyze")
def create_analysis(job: JobDescription, db: Session = Depends(get_db)):
    result = analyze_job_description(job.description, job.num_candidates)
    db_analysis = models.JobAnalysis(description=job.description, result=result)
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)
    return db_analysis


@app.get("/analyses")
def get_analyses(db: Session = Depends(get_db)):
    analyses = db.query(models.JobAnalysis).all()
    return [
        {
            "id": analysis.id,
            "description": analysis.description,
            "result": json.loads(analysis.result),
        }
        for analysis in analyses
    ]
