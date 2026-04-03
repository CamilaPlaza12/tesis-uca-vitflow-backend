from pydantic import BaseModel, Field, EmailStr, model_validator
from pydantic import ConfigDict
from typing import Literal, Optional, List

BloodGroup = Literal[
    "O+", "O-",
    "A+", "A-",
    "B+", "B-",
    "AB+", "AB-"
]

Gender = Literal["F", "M", "OTHER"]
EligibilityStatus = Literal["APT", "WAIT", "NOT_APT"]


class GeoPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class AddressValidationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    address_text: str = Field(..., min_length=5, max_length=180)


class AddressValidationOut(BaseModel):
    ok: bool
    address_text: str
    geo: Optional[GeoPoint] = None


class DonorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    dni: str = Field(..., min_length=6, max_length=15)

    email: EmailStr
    phone_number: str = Field(..., min_length=6, max_length=20, pattern=r"^\+?[0-9\s\-()]{6,20}$")

    gender: Gender
    is_pregnant: Optional[bool] = Field(
        default=None,
        description="Legacy field. Only applicable if gender is 'F'. Must be null otherwise."
    )
    is_currently_pregnant: Optional[bool] = Field(
        default=None,
        description="New field for current pregnancy status."
    )
    medications: Optional[List[str]] = None

    birth_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    weight_kg: float = Field(..., gt=0, le=300)

    blood_group: BloodGroup
    has_recent_tattoo: bool = False
    last_tattoo_or_piercing_date: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )

    last_donation_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    last_pregnancy_end_date: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )
    pregnancy_end_type: Optional[Literal["VAGINAL_BIRTH", "CESAREAN", "NON_SPONTANEOUS_ABORTION"]] = None
    is_breastfeeding: Optional[bool] = None

    address_text: str = Field(..., min_length=5, max_length=180)

    is_subscribed: bool = True
    has_consent: bool = True
    is_enabled: bool = True

    has_fever_or_infection: bool = False
    has_active_fever_or_infection: Optional[bool] = None
    infection_resolved_date: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )

    screening_updated_at: Optional[str] = None

    @model_validator(mode="after")
    def validate_pregnancy_consistency(self):
        if self.gender != "F":
            if self.is_pregnant is not None:
                raise ValueError("is_pregnant must be null unless gender is 'F'")
            if self.is_currently_pregnant is not None:
                raise ValueError("is_currently_pregnant must be null unless gender is 'F'")
            if self.last_pregnancy_end_date is not None:
                raise ValueError("last_pregnancy_end_date must be null unless gender is 'F'")
            if self.pregnancy_end_type is not None:
                raise ValueError("pregnancy_end_type must be null unless gender is 'F'")
            if self.is_breastfeeding is not None:
                raise ValueError("is_breastfeeding must be null unless gender is 'F'")

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
    is_currently_pregnant: Optional[bool]
    medications: Optional[List[str]]

    birth_date: str
    age_years: int

    weight_kg: float
    blood_group: BloodGroup

    has_recent_tattoo: bool
    last_tattoo_or_piercing_date: Optional[str]
    last_donation_date: Optional[str]

    last_pregnancy_end_date: Optional[str]
    pregnancy_end_type: Optional[str]
    is_breastfeeding: Optional[bool]

    address_text: str
    geo: GeoPoint

    is_subscribed: bool
    has_consent: bool
    is_enabled: bool

    has_fever_or_infection: bool = False
    has_active_fever_or_infection: Optional[bool] = None
    infection_resolved_date: Optional[str] = None
    screening_updated_at: Optional[str] = None

    eligibility_status: Optional[EligibilityStatus] = None
    eligibility_available_from: Optional[str] = None
    eligibility_checked_at: Optional[str] = None
    eligibility_reasons: Optional[List[str]] = None


class DonorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weight_kg: Optional[float] = Field(None, gt=0, le=300)
    has_recent_tattoo: Optional[bool] = None
    last_tattoo_or_piercing_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    last_donation_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    address_text: Optional[str] = Field(None, min_length=5, max_length=180)

    is_pregnant: Optional[bool] = None
    is_currently_pregnant: Optional[bool] = None
    last_pregnancy_end_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    pregnancy_end_type: Optional[Literal["VAGINAL_BIRTH", "CESAREAN", "NON_SPONTANEOUS_ABORTION"]] = None
    is_breastfeeding: Optional[bool] = None

    medications: Optional[List[str]] = None
    has_fever_or_infection: Optional[bool] = None
    has_active_fever_or_infection: Optional[bool] = None
    infection_resolved_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    screening_updated_at: Optional[str] = None

    is_subscribed: Optional[bool] = None
    has_consent: Optional[bool] = None
    is_enabled: Optional[bool] = None