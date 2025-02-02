from pydantic import BaseModel
from typing import Optional


class UserTemplates(BaseModel):
    """Model for user's templates"""

    linkedin_template: Optional[str] = None
    email_template: Optional[str] = None


class TemplateUpdateRequest(BaseModel):
    """Model for updating both templates at once"""

    linkedin_template: Optional[str] = None  # Content of LinkedIn template
    email_template: Optional[str] = None  # Content of email template


class CustomInstructions(BaseModel):
    """Model for user's custom evaluation instructions"""

    evaluation_instructions: Optional[str] = None
