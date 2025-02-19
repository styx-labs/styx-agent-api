from pydantic import BaseModel


class UserTemplates(BaseModel):
    """Model for user's templates"""

    linkedin_template: str | None
    email_template: str | None


class TemplateUpdateRequest(BaseModel):
    """Model for updating both templates at once"""

    linkedin_template: str | None
    email_template: str | None


class CustomInstructions(BaseModel):
    """Model for user's custom evaluation instructions"""

    evaluation_instructions: str | None
