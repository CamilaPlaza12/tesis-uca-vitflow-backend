from pydantic import BaseModel, Field, model_validator
from typing import Dict, Literal

Weekday = Literal["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"]

class HospitalAvailability(BaseModel):
    weekly: Dict[Weekday, Dict[str, int]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_weekly(self):
        for day, slots in self.weekly.items():
            if slots is None:
                continue

            for t, cap in slots.items():
                if not isinstance(t, str) or len(t) != 5 or t[2] != ":":
                    raise ValueError(f"Invalid time '{t}' in {day}. Use HH:MM.")

                hh_str, mm_str = t.split(":", 1)
                if not (hh_str.isdigit() and mm_str.isdigit()):
                    raise ValueError(f"Invalid time '{t}' in {day}. Use HH:MM with numbers.")

                hh = int(hh_str)
                mm = int(mm_str)

                if hh < 0 or hh > 23 or mm < 0 or mm > 59:
                    raise ValueError(f"Invalid time '{t}' in {day}. Hour 0-23, minute 0-59.")

                if mm % 5 != 0:
                    raise ValueError(f"Invalid time '{t}' in {day}. Minutes must be divisible by 5.")

                if not isinstance(cap, int) or cap < 1 or cap > 500:
                    raise ValueError(f"Invalid capacity for {day} {t}: {cap} (1..500).")

        return self

class HospitalAvailabilityDB(HospitalAvailability):
    hospital_id: str
