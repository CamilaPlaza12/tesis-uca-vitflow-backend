from pydantic import BaseModel, Field
from typing import Literal, Optional

HospitalRequestPriority = Literal["NORMAL", "URGENTE", "CRITICA"]
HospitalRequestStatus = Literal["ACTIVO", "COMPLETO", "CANCELADO", "FINALIZADO"]

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
    requested_ml: int = Field(..., ge=1, le=20000)  # cantidadSolicitadaMl
    priority: HospitalRequestPriority
    requested_by: str = Field(..., min_length=1, max_length=100)
    comments: Optional[str] = Field(None, max_length=500)

class HospitalRequest(BaseModel):
    datetime_local: str
    hospital_unit: HospitalUnit
    component: str
    blood_group: str
    requested_ml: int
    collected_ml: int = 0
    priority: HospitalRequestPriority
    status: HospitalRequestStatus
    requested_by: str
    comments: Optional[str] = None

class HospitalRequestDB(HospitalRequest):
    hospital_id: str

class UpdateHospitalRequestStatusRequest(BaseModel):
    status: HospitalRequestStatus

class UpdateHospitalRequestRequest(BaseModel):
    hospital_unit: Optional[HospitalUnit] = None
    priority: Optional[HospitalRequestPriority] = None
    status: Optional[HospitalRequestStatus] = None
    comments: Optional[str] = Field(None, max_length=500)


