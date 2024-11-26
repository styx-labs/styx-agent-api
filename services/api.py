from google.cloud import firestore
from services.azure_openai import get_azure_openai
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector


class Api:
    def __init__(self):
        self.db = firestore.Client(database="people-db-prod")

    def create_candidate(self, payload, urn_id):
        self.db.collection("linkedin").document(urn_id).set(payload)

    def delete_candidate(self, urn_id):
        self.db.collection("linkedin").document(urn_id).delete()

    def get_filtered_candidates(self, job_description: str, num_candidates: int, school_list: list[str], location_list: list[str], graduation_year_upper_bound: str, graduation_year_lower_bound: str):
        query = self.db.collection("linkedin")

        if graduation_year_lower_bound:
            query = query.where("graduation_year", ">=", graduation_year_lower_bound)
        if graduation_year_upper_bound:
            query = query.where("graduation_year", "<=", graduation_year_upper_bound)
        
        if school_list:
            query = query.where("schools", "array_contains_any", school_list)

        if location_list:
            query = query.where("location", "in", location_list)

        openai_client = get_azure_openai()

        emb = (
            openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=job_description,
            )
            .data[0]
            .embedding
        )

        query = query.find_nearest(
            vector_field="embedding",
            query_vector=Vector(emb),
            distance_measure=DistanceMeasure.COSINE,
            limit=num_candidates
        )

        results = [{
            'candidate_first_name': candidate.get('candidate_first_name'),
            'candidate_last_name': candidate.get('candidate_last_name'), 
            'candidate_desc': candidate.get('candidate_desc')
        } for candidate in query.stream()]
        return results
