from firebase_admin import auth, credentials, initialize_app
import firebase_admin
from fastapi import HTTPException, status

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    initialize_app(cred)


async def verify_firebase_token(token: str) -> str:
    """
    Verify Firebase ID token and return the user ID
    """
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token["uid"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
        )
