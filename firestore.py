from google.cloud import firestore
import os

# Initialize Firestore client
db = firestore.Client(database=os.getenv("DB"))


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
