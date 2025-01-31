from pydantic import BaseModel
from typing import Optional

class CustomInstructions(BaseModel):
    """Model for user's custom evaluation instructions"""
    evaluation_instructions: Optional[str] = None 