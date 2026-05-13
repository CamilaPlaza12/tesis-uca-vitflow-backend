from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal

BloodGroup = Literal["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
EligibilityStatus = Literal["APT", "WAIT", "NOT_APT"]


class NearbyDonorOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    dni: str
    email: EmailStr
    phone_number: str
    blood_group: BloodGroup
    eligibility_status: Optional[EligibilityStatus] = None
    distance_km: float = Field(..., ge=0)


class NearbyDonorsResponse(BaseModel):
    hospital_request_id: str
    hospital_id: str
    blood_group: BloodGroup
    radius_km: float
    total: int
    donors: List[NearbyDonorOut]