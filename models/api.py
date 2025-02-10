from typing import List, Optional
from datetime import datetime
from pydantic import Field
from .base import SerializableModel, Candidate
from models.linkedin import LinkedInProfile


class EditKeyTraitsPayload(SerializableModel):
    """Payload for editing key traits"""

    key_traits: List[dict]


class HeadlessEvaluatePayload(Candidate):
    """Payload for headless evaluation"""

    job_description: str = None


class ReachoutPayload(SerializableModel):
    """Payload for reachout request"""

    format: str


class HeadlessReachoutPayload(SerializableModel):
    """Payload for headless reachout"""

    name: str
    job_description: str
    sections: List[dict]
    citations: List[dict]


class Calibration(SerializableModel):
    """Calibration model"""

    url: Optional[str] = None
    candidate: Optional[LinkedInProfile] = None
    calibration_result: str


class HeadlessEvaluationPayload(SerializableModel):
    """Payload for headless evaluation"""

    url: Optional[str] = None
    candidate: Optional[LinkedInProfile] = None
    job_description: str
    calibrations: Optional[List[Calibration]] = None


class ParaformEvaluateGraphPayload(SerializableModel):
    """Payload for Paraform graph evaluation"""

    candidate_context: str
    candidate_full_name: str
    number_of_roles: int


class ParaformEvaluateGraphLinkedinPayload(SerializableModel):
    """Payload for Paraform LinkedIn evaluation"""

    linkedin_url: str
    number_of_queries: int


class BulkLinkedInPayload(SerializableModel):
    """Payload for bulk LinkedIn processing"""

    urls: List[str]
    search_mode: bool = True


class GetEmailPayload(SerializableModel):
    """Payload for email retrieval"""

    linkedin_profile_url: str


class CheckoutSessionRequest(SerializableModel):
    """Request for creating checkout session"""

    planId: str


class TestTemplateRequest(SerializableModel):
    """Request for testing template"""

    format: str
    template_content: str
