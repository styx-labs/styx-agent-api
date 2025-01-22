import google_crc32c
from google.cloud import secretmanager
from dotenv import load_dotenv
import os

load_dotenv()


def get_secret(secret_id: str, version_id: str):
    client = secretmanager.SecretManagerServiceClient()
    crc32c = google_crc32c.Checksum()
    name = f"projects/{os.getenv('PROJECT_ID')}/secrets/{secret_id}/versions/{version_id}"

    response = client.access_secret_version(request={"name": name})

    crc32c.update(response.payload.data)
    if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
        print("Data corruption detected.")
        return None

    return response.payload.data.decode("UTF-8")
