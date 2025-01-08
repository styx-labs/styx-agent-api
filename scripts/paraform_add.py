import sys
import os
from google.cloud import firestore
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.azure_openai import llm
from langchain_core.messages import HumanMessage
import tqdm


db = firestore.Client(database="unilink-agent-db-prod")
paraform_ref = db.collection("paraform-jobs")
user_ref = db.collection("users").document("FKMnAfCPMITMDyMnraOBC9lrImI2").collection("jobs")


for job in tqdm.tqdm(paraform_ref.stream(), desc="Processing jobs"):
    job_data = {}
    paraform_job = job.to_dict()
    job_data["company_name"] = paraform_job["company_name"]
    job_data["job_title"] = paraform_job["name"]
    job_data["job_description"] = paraform_job["role_description"]
    job_data["embedding"] = paraform_job["embedding"]

    key_traits = []
    for requirement in paraform_job["requirements"]:
        prompt = f"Please distill the following job requirement into a 3-5 word trait: {requirement}"
        response = llm.invoke(
            [HumanMessage(
                content=prompt.format(requirement=requirement)
            )]
        )
        key_traits.append({"trait": response.content, "description": requirement})
    job_data["key_traits"] = key_traits
    user_ref.add(job_data)
