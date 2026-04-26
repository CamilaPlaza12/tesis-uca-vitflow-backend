from pydantic import BaseModel, Field
from typing import Literal, Optional

HospitalRequestPriority = Literal["NORMAL", "URGENTE", "CRITICA"]
HospitalRequestStatus = Literal["ACTIVO", "COMPLETO", "CANCELADO", "FINALIZADO"]
HospitalRequestType = Literal["NORMAL", "CAMPAÑA"]
PedidoTipo = Literal["manual", "automatico", "evento"]

HospitalUnit = Literal[
    "ITU",
    "Terapia Intensiva",
    "Guardia",
    "Quirofano",
    "Clinica Medica"
]


class HospitalRequestCreate(BaseModel):
    hospital_unit: HospitalUnit
    component: str = Field(..., min_length=1, max_length=100)
    blood_group: str = Field(..., min_length=2, max_length=4)
    priority: HospitalRequestPriority
    requested_by: str = Field(..., min_length=1, max_length=100)
    comments: Optional[str] = Field(None, max_length=500)

    request_type: HospitalRequestType = "NORMAL"
    tipo: PedidoTipo = "manual"
    end_date: str = Field(..., min_length=10, max_length=40)


class HospitalRequest(BaseModel):
    datetime_local: str
    hospital_unit: HospitalUnit
    component: str
    blood_group: str
    priority: HospitalRequestPriority
    status: HospitalRequestStatus
    requested_by: str
    comments: Optional[str] = None

    request_type: HospitalRequestType = "NORMAL"
    tipo: PedidoTipo = "manual"
    end_date: str


class HospitalRequestDB(HospitalRequest):
    hospital_id: str


class UpdateHospitalRequestStatusRequest(BaseModel):
    status: HospitalRequestStatus


class UpdateHospitalRequestRequest(BaseModel):
    hospital_unit: Optional[HospitalUnit] = None
    priority: Optional[HospitalRequestPriority] = None
    status: Optional[HospitalRequestStatus] = None
    comments: Optional[str] = Field(None, max_length=500)

    request_type: Optional[HospitalRequestType] = None
    tipo: Optional[PedidoTipo] = None
    end_date: Optional[str] = Field(None, min_length=10, max_length=40)