from pydantic import BaseModel, Field
from typing import Literal, Optional

RejectionReason = Literal["not_now", "opt_out", "no_response"]


class DonorRejectionRequest(BaseModel):
    hospital_request_id: str = Field(..., min_length=1)
    reason: RejectionReason
    notes: Optional[str] = Field(None, max_length=500)


class DonorRejectionOut(BaseModel):
    donor_id: str
    hospital_request_id: str
    reason: RejectionReason
    recorded_at: str
    is_subscribed: bool
