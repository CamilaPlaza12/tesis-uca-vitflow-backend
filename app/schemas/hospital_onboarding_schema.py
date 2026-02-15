from pydantic import BaseModel, Field, EmailStr
from typing import Literal, Optional

OnboardingStatus = Literal["SUBMITTED", "APPROVED", "REJECTED"]


class HospitalAddress(BaseModel):
    province: str = Field(..., min_length=2, max_length=80)
    localidad: str = Field(..., min_length=2, max_length=80)
    city: str = Field(..., min_length=2, max_length=80)
    street: str = Field(..., min_length=2, max_length=120)
    number: str = Field(..., min_length=1, max_length=10)
    provinceId: str
    localidadId: str


class HospitalData(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    email: EmailStr
    phone: str = Field(..., min_length=6, max_length=20)
    logoFile: Optional[str] = None
    address: HospitalAddress


class AdminData(BaseModel):
    firstName: str = Field(..., min_length=2, max_length=40)
    lastName: str = Field(..., min_length=2, max_length=40)
    email: EmailStr
    phone: str = Field(..., min_length=6, max_length=20)
    dni: str = Field(..., pattern=r"^\d{7,8}$")


class HospitalOnboardingRequestCreate(BaseModel):
    hospital: HospitalData
    admin: AdminData
    status: OnboardingStatus
    createdAt: str
    updatedAt: str


class HospitalOnboardingRequestReview(BaseModel):
    status: OnboardingStatus
    reviewedBy: Optional[str] = None
    reviewedAt: Optional[str] = None
    reviewNote: Optional[str] = None
