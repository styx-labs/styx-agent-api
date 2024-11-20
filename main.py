from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

# from langflow.load import run_flow_from_json
from firestore import add_analysis, get_all_analyses, remove_analysis
import datetime
from agents.run_search_chain import RunSearchChain


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


class JobDescription(BaseModel):
    description: str
    num_candidates: int


def analyze_job_description(description: str, num: int) -> str:
    result = RunSearchChain.run_search(description, str(num))
    
    while result and not result.startswith('{'):
        result = result[1:]
        
    while result and not result.endswith('}'):
        result = result[:-1]
        
    return result


@app.post("/analyze")
def create_analysis(job: JobDescription):
    result = analyze_job_description(job.description, job.num_candidates)
    # Convert result string to dict if it's a JSON string
    result_dict = json.loads(result) if isinstance(result, str) else result

    analysis_data = {
        "description": job.description,
        "result": result_dict,
        "timestamp": datetime.datetime.now(),
    }

    # Add to Firestore
    doc_id = add_analysis(analysis_data)

    # Return the created analysis with its ID
    return {"id": doc_id, **analysis_data}


@app.get("/analyses")
def get_analyses():
    analyses = get_all_analyses()
    return analyses


@app.delete("/analyses/{doc_id}")
def delete_analysis(doc_id: str):
    return remove_analysis(doc_id)
