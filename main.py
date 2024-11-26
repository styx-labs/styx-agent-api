from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import json
from firestore import add_analysis, get_all_analyses, remove_analysis, get_all_locations, get_all_schools
import datetime
from agents.run_search_chain import RunSearchChain
from agents.prompts import key_traits_prompt
from services.azure_openai import get_azure_openai
from models import Analysis, JobDescription


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://unilink-agent-ui-16250094868.us-central1.run.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def analyze_job_description(analysis: Analysis) -> str:
    result = RunSearchChain.run_search(analysis)
    
    while result and not result.startswith('{'):
        result = result[1:]
        
    while result and not result.endswith('}'):
        result = result[:-1]
        
    return result


@app.post("/analyze")
def create_analysis(analysis: Analysis):
    result = analyze_job_description(analysis)
    result_dict = json.loads(result) if isinstance(result, str) else result

    analysis_data = {
        "description": analysis.job_description,
        "result": result_dict,
        "timestamp": datetime.datetime.now(),
        "key_traits": analysis.key_traits,
        "school_list": analysis.school_list,
        "location_list": analysis.location_list,
        "graduation_year_upper_bound": analysis.graduation_year_upper_bound,
        "graduation_year_lower_bound": analysis.graduation_year_lower_bound,
    }

    # Add to Firestore
    doc_id = add_analysis(analysis_data)

    # Return the created analysis with its ID
    return {"id": doc_id, **analysis_data}


@app.post("/get-key-traits")
def get_key_traits(job: JobDescription):
    client = get_azure_openai()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": key_traits_prompt}, {"role": "user", "content": job.description}],
        response_format={"type": "json_object"}
    )
    traits = json.loads(response.choices[0].message.content)["key_traits"]
    return {"key_traits": traits}

@app.get("/analyses")
def get_analyses():
    analyses = get_all_analyses()
    return analyses


@app.delete("/analyses/{doc_id}")
def delete_analysis(doc_id: str):
    return remove_analysis(doc_id)

@app.get("/locations")
def get_locations():
    return get_all_locations()

@app.get("/schools")
def get_schools():
    return get_all_schools()
