from google.cloud import firestore
import os
import dotenv

dotenv.load_dotenv()

db = firestore.Client(database=os.getenv("DB"))
people_db = firestore.Client(database=os.getenv("PEOPLE_DB"))


def add_analysis(analysis_data):
    """
    Add a new analysis to Firestore

    Args:
        analysis_data (dict): Dictionary containing analysis data

    Returns:
        str: Document ID of the created analysis
    """
    # Reference to analyses collection
    analyses_ref = db.collection("analyses")

    # Add a new document with a generated ID
    doc_ref = analyses_ref.document()
    doc_ref.set(analysis_data)

    return doc_ref.id


def remove_analysis(doc_id):
    db.collection("analyses").document(doc_id).delete()
    return True


def get_all_analyses():
    """
    Retrieve all analyses from Firestore

    Returns:
        list: List of analysis documents
    """
    analyses_ref = db.collection("analyses")

    # Get all documents, ordered by timestamp descending
    docs = analyses_ref.order_by(
        "timestamp", direction=firestore.Query.DESCENDING
    ).stream()

    # Convert to list of dictionaries
    analyses = []
    for doc in docs:
        analysis_data = doc.to_dict()
        analyses.append(
            {
                "id": doc.id,
                "description": analysis_data.get("description"),
                "result": analysis_data.get("result"),
                "timestamp": analysis_data.get("timestamp"),
            }
        )

    return analyses

def get_all_locations():
    """
    Retrieve all locations from Firestore

    Returns:
        list: List of locations
    """
    docs = people_db.collection("locations").stream()

    locations = []
    for doc in docs:
        loc = doc.to_dict()
        locations.append(loc["location"])

    return locations

def get_all_schools():
    """
    Retrieve all schools from Firestore

    Returns:
        list: List of schools
    """
    docs = people_db.collection("schools").stream()

    schools = []
    for doc in docs:
        school = doc.to_dict()
        schools.append(school["school"])

    return schools
