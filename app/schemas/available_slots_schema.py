from pydantic import BaseModel, Field
from datetime import date

class AvailableSlot(BaseModel):
    date_local: date
    time_local: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    capacity: int = Field(..., ge=1, le=500)
    used: int = Field(0, ge=0)

class AvailableSlotDB(AvailableSlot):
    hospital_id: str
    slot_key: str