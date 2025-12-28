from pydantic import BaseModel, Field
from typing import Literal, Optional

HospitalRequestPriority = Literal["NORMAL", "URGENTE", "CRITICO"]
HospitalRequestStatus = Literal["ACTIVO", "COMPLETADO", "CANCELADO"]

HospitalUnit = Literal[
    "ITU",
    "TERAPIA_INTENSIVA",
    "GUARDIA",
    "QUIROFANO",
    "CLINICA_MEDICA"
]

class HospitalRequestCreate(BaseModel):
    hospital_unit: HospitalUnit
    component: str = Field(..., min_length=1, max_length=100)
    blood_group: str = Field(..., min_length=2, max_length=4)
    quantity: int = Field(..., ge=1, le=50)
    priority: HospitalRequestPriority
    requested_by: str = Field(..., min_length=1, max_length=100)
    comments: Optional[str] = Field(None, max_length=500)

class HospitalRequest(BaseModel):
    datetime_local: str
    hospital_unit: HospitalUnit
    component: str
    blood_group: str
    quantity: int
    priority: HospitalRequestPriority
    status: HospitalRequestStatus
    requested_by: str
    comments: Optional[str] = None

class HospitalRequestDB(HospitalRequest):
    hospital_id: str

class UpdateHospitalRequestStatusRequest(BaseModel):
    status: HospitalRequestStatus
