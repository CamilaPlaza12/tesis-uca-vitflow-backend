from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import Literal, Optional, List

BloodGroup = Literal[
    "O+", "O-",
    "A+", "A-",
    "B+", "B-",
    "AB+", "AB-"
]

Gender = Literal["F", "M", "OTHER"]

class GeoPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class DonorCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    dni: str = Field(..., min_length=6, max_length=15)

    email: EmailStr
    phone_number: str = Field(..., min_length=6, max_length=20, pattern=r"^\+?[0-9\s\-()]{6,20}$")

    gender: Gender
    is_pregnant: Optional[bool] = Field(..., description="Only applicable if gender is 'F'. Must be null otherwise.")
    medications: Optional[List[str]] = None

    birth_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    weight_kg: float = Field(..., gt=0, le=300)

    blood_group: BloodGroup
    has_recent_tattoo: bool = False

    last_donation_date: Optional[str] = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")

    address_text: str = Field(..., min_length=5, max_length=180)

    # ✅ ahora lo completa el backend (si viene, también lo aceptamos)
    geo: Optional[GeoPoint] = None

    is_subscribed: bool = True
    has_consent: bool = True

    @model_validator(mode="after")
    def validate_pregnancy_consistency(self):
        if self.gender != "F" and self.is_pregnant is not None:
            raise ValueError("is_pregnant must be null unless gender is 'F'")
        return self

class Donor(BaseModel):
    id: str
    first_name: str
    last_name: str
    dni: str

    email: EmailStr
    phone_number: str

    gender: Gender
    is_pregnant: Optional[bool]
    medications: Optional[List[str]]

    birth_date: str
    weight_kg: float
    blood_group: BloodGroup

    has_recent_tattoo: bool
    last_donation_date: Optional[str]

    address_text: str
    geo: GeoPoint  # ✅ en response debería existir

    is_subscribed: bool
    has_consent: bool

    created_at_local: str
    updated_at_local: Optional[str] = None

class DonorUpdate(BaseModel):
    weight_kg: Optional[float] = Field(None, gt=0, le=300)
    has_recent_tattoo: Optional[bool] = None
    last_donation_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    address_text: Optional[str] = Field(None, min_length=5, max_length=180)
    geo: Optional[GeoPoint] = None
