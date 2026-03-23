from pydantic import BaseModel, EmailStr, Field
from typing import Literal


UserRole = Literal["HOSPITAL_ADMIN", "TECHNICIAN"]
UserStatus = Literal["INVITED", "ACTIVE", "SUSPENDED"]


class Address(BaseModel):
    street: str = Field(..., min_length=1, max_length=100)
    number: str = Field(..., min_length=1, max_length=10)
    locality: str = Field(..., min_length=1, max_length=100)
    city: str = Field(..., min_length=1, max_length=100)
    province: str = Field(..., min_length=1, max_length=100)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=6, max_length=20)
    address: Address


class UserResponse(BaseModel):
    uid: str
    email: EmailStr | None = None
    full_name: str | None = None
    phone_number: str | None = None
    address: Address | None = None
    role: UserRole | None = None
    status: UserStatus | None = None