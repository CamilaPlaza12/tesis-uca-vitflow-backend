from pydantic import BaseModel, Field
from typing import Literal
from datetime import date

DonationType = Literal["SANGRE", "PLAQUETAS", "MEDULA_OSEA"]
AppointmentStatus = Literal["PROGRAMADO", "CONFIRMADO", "CANCELADO", "COMPLETADO", "NO_PRESENTADO"]
AppointmentSource = Literal["HOSPITAL_MANUAL", "CHATBOT_WHATSAPP"]

class Donor(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    dni: str = Field(..., min_length=6, max_length=10)


class AppointmentCreate(BaseModel):
    hospital_request_id: str = Field(..., min_length=1)
    date_local: date
    time_local: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    donor: Donor
    donation_type: DonationType

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
