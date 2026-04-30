from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import date

DonationType = Literal["SANGRE", "PLAQUETAS", "MEDULA_OSEA"]
AppointmentStatus = Literal[
    "PROGRAMADO",
    "CONFIRMADO",
    "PENDIENTE_CLASIFICACION",
    "COMPLETADO",
    "CANCELADO",
    "NO_PRESENTADO",
]
AppointmentSource = Literal["HOSPITAL_MANUAL", "VITO_WHATSAPP"]


class Donor(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    dni: str = Field(..., min_length=6, max_length=10)


class AppointmentCreate(BaseModel):
    hospital_request_id: str = Field(..., min_length=1)
    date_local: date
    time_local: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    donor: Donor
    donation_type: DonationType


class AppointmentCreateFromVito(BaseModel):
    donor_id: str = Field(..., min_length=1)
    hospital_request_id: str = Field(..., min_length=1)
    date_local: date
    time_local: str = Field(..., pattern=r"^\d{2}:\d{2}$")


class Appointment(BaseModel):
    hospital_request_id: str
    date_local: date
    time_local: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    donor: Donor
    donation_type: DonationType
    status: AppointmentStatus
    source: AppointmentSource


class AppointmentDB(Appointment):
    hospital_id: str


class UpdateAppointmentStatusRequest(BaseModel):
    status: AppointmentStatus


class RescheduleAppointmentRequest(BaseModel):
    date_local: date
    time_local: str = Field(..., pattern=r"^\d{2}:\d{2}$")


Componente = Literal["globulos_rojos", "plasma", "plaquetas"]
BloodGroup = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


class ConfirmarAsistenciaRequest(BaseModel):
    """
    Body para marcar la asistencia de un donante y registrar los componentes obtenidos.
    Cambia el turno a COMPLETADO y crea una unidad por cada componente seleccionado.
    Si blood_group es None, se resuelve automáticamente desde el perfil del donante.
    """
    blood_group: Optional[BloodGroup] = None
    componentes: List[Componente] = Field(..., min_length=1)


class UnidadResumen(BaseModel):
    id: str
    componente: str
    blood_group: str
    fecha_vencimiento: str
    estado: str


class ConfirmarAsistenciaOut(BaseModel):
    appointment_id: str
    status: str
    unidades_creadas: List[UnidadResumen]