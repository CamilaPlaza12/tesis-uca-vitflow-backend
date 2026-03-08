from pydantic import BaseModel, Field
from typing import Dict, Literal, Optional

BloodType = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

DEFAULT_STOCKS: Dict[str, int] = {
    "A+": 0, "A-": 0, "B+": 0, "B-": 0,
    "AB+": 0, "AB-": 0, "O+": 0, "O-": 0,
}

DEFAULT_THRESHOLDS: Dict[str, int] = {
    "A+": 0, "A-": 0, "B+": 0, "B-": 0,
    "AB+": 0, "AB-": 0, "O+": 0, "O-": 0,
}

class BloodBankOut(BaseModel):
    hospital_id: str
    stocks_ml: Dict[BloodType, int] = Field(default_factory=dict)
    thresholds_ml: Dict[BloodType, int] = Field(default_factory=dict)

class BloodBankAdjustRequest(BaseModel):
    blood_type: BloodType
    amount_ml: int = Field(..., gt=0, le=5_000_000)  # vos ajustá el max si querés

class BloodBankThresholdsUpdateRequest(BaseModel):
    thresholds_ml: Dict[BloodType, int] = Field(default_factory=dict)
