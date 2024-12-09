import sys
import os
import requests
from google.cloud.firestore_v1.vector import Vector
from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.azure_openai import get_azure_openai
import re
from nltk.corpus import stopwords
import nltk
from tqdm import tqdm


nltk.download('stopwords', quiet=True)

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    stop_words = set(stopwords.words("english"))
    words = text.split()
    words = [word for word in words if word not in stop_words]
    text = ' '.join(words)
    return words

db = firestore.Client(database="unilink-agent-db-prod")
openai_client = get_azure_openai()

jobs = requests.get("https://www.paraform.com/api/roles/public")

jobs = jobs.json()
jobs = tqdm(jobs, desc="Processing jobs")
for job in jobs:
    job_str = ""
    job_str += job["role_description"] + "\n"
    for requirement in job["requirements"]:
        job_str += requirement + "\n"
    for responsibility in job["responsibilities"]:
        job_str += responsibility + "\n"
    job_str += job["experience_info"] + "\n"

    emb = (
        openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=job_str,
        )
        .data[0]
        .embedding
    )

    job["embedding"] = Vector(emb)
    db.collection("paraform-jobs").add(job)
