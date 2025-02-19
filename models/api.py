from typing import Optional
from .serializable import SerializableModel
from .jobs import Candidate, CalibratedProfiles
from .linkedin import LinkedInProfile


class EditKeyTraitsPayload(SerializableModel):
    """Payload for editing key traits"""

    key_traits: list[dict]


class EditKeyTraitsLLMPayload(SerializableModel):
    """Payload for editing key traits with LLM"""

    prompt: str


class EditJobDescriptionPayload(SerializableModel):
    """Payload for editing job description"""

    job_description: str


class EditJobDescriptionLLMPayload(SerializableModel):
    """Payload for editing job description with LLM"""

    prompt: str


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
    sections: list[dict]
    citations: list[dict]


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
    calibrations: Optional[list[Calibration]] = []


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

    urls: list[str]
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


class CandidateCalibrationPayload(SerializableModel):
    """Payload for individual candidate calibration"""

    fit: str  # "good" or "bad"
    reasoning: str


class BulkCalibrationPayload(SerializableModel):
    """Payload for bulk candidate calibration"""

    feedback: dict[str, CandidateCalibrationPayload]  # Dict of candidate_id to feedback


class UpdateCalibratedProfilesPayload(SerializableModel):
    """Payload for updating calibrated profiles"""

    calibrated_profiles: list[CalibratedProfiles]


class BulkCandidatePayload(SerializableModel):
    """Payload for bulk candidate processing"""

    candidate_ids: list[str]
