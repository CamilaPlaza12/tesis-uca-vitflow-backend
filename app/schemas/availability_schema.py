from pydantic import BaseModel, Field, model_validator
from typing import Dict, Literal
from datetime import timedelta, datetime

Weekday = Literal["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"]

def generate_allowed_times(start_hhmm: str = "07:00", end_hhmm: str = "20:00", step_minutes: int = 30) -> list[str]:
    """
    Genera grilla desde start inclusive hasta end EXCLUSIVO.
    Ej: 07:00..20:00 cada 30 => último es 19:30
    """
    sh, sm = map(int, start_hhmm.split(":"))
    eh, em = map(int, end_hhmm.split(":"))

    start = datetime(2000, 1, 1, sh, sm)
    end = datetime(2000, 1, 1, eh, em)

    out: list[str] = []
    cur = start
    step = timedelta(minutes=step_minutes)

    while cur < end:  # <- último 19:30
        out.append(cur.strftime("%H:%M"))
        cur += step

    return out

ALLOWED_WEEKDAYS: list[str] = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"]
ALLOWED_TIMES_LIST: list[str] = generate_allowed_times("07:00", "20:00", 30)
ALLOWED_TIMES_SET = set(ALLOWED_TIMES_LIST)

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

                if t not in ALLOWED_TIMES_SET:
                    raise ValueError(
                        f"Time '{t}' in {day} is not allowed. Allowed times: 07:00 to 19:30 every 30 minutes."
                    )

                if not isinstance(cap, int) or cap < 1 or cap > 500:
                    raise ValueError(f"Invalid capacity for {day} {t}: {cap} (1..500).")

        return self

class HospitalAvailabilityDB(HospitalAvailability):
    hospital_id: str

class AvailabilityOptions(BaseModel):
    weekdays: list[str]
    times: list[str]
