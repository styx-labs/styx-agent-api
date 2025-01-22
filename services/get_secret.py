from google.cloud import secretmanager
from dotenv import load_dotenv
import os

load_dotenv()


def get_secret(secret_id: str, version_id: str):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{os.getenv('PROJECT_ID')}/secrets/{secret_id}/versions/{version_id}"

    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
