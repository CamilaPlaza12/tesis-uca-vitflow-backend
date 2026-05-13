from pydantic import BaseModel, Field, EmailStr
from typing import Literal

PlanId = Literal["FREE", "PRO"]
SubscriptionStatus = Literal["PENDING_PAYMENT", "ACTIVE", "CANCELLED"]

class HospitalAddress(BaseModel):
    province: str = Field(..., min_length=2, max_length=80)
    localidad: str = Field(..., min_length=2, max_length=80)
    city: str = Field(..., min_length=2, max_length=80)
    street: str = Field(..., min_length=2, max_length=120)
    number: str = Field(..., min_length=1, max_length=10)

class HospitalCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    email: EmailStr
    phone: str = Field(..., min_length=6, max_length=20)

    address: HospitalAddress

    planId: PlanId

    subscriptionStatus: SubscriptionStatus = "PENDING_PAYMENT"

    createdAt: str

    createdFromRequestId: str
