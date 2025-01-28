from pydantic import BaseModel
from typing import Optional


class MessageTemplate(BaseModel):
    """Base model for message templates"""

    template_id: Optional[str] = None
    content: str
    template_type: str  # 'linkedin' or 'email'
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


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
