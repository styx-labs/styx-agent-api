from pydantic import BaseModel


class CustomInstructions(BaseModel):
    """Model for user's custom evaluation instructions"""

    evaluation_instructions: str | None
