from pydantic import BaseModel, Field, model_validator
from typing import List, Literal

Weekday = Literal[
    "Lunes",
    "Martes",
    "Miercoles",
    "Jueves",
    "Viernes",
    "Sabado",
    "Domingo",
]

ALL_DAYS = {"Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"}


class TimeSlot(BaseModel):
    time: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # "HH:mm"
    capacity: int = Field(..., ge=1, le=999)


class AvailabilityDay(BaseModel):
    day: Weekday
    enabled: bool = False
    timeSlots: List[TimeSlot] = Field(default_factory=list)


class HospitalAvailabilityIn(BaseModel):
    # ✅ request: el front manda SOLO days
    days: List[AvailabilityDay] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_days(self):
        # 0) deben venir exactamente 7 días
        if len(self.days) != 7:
            raise ValueError("days must contain exactly 7 items (one per weekday).")

        # 1) deben ser exactamente los 7 días, sin repetir
        day_list = [d.day for d in self.days]
        day_set = set(day_list)

        if len(day_set) != 7:
            raise ValueError("Duplicate day entries in days. Each day must appear once.")

        if day_set != ALL_DAYS:
            missing = sorted(list(ALL_DAYS - day_set))
            extra = sorted(list(day_set - ALL_DAYS))
            raise ValueError(f"days must contain all weekdays. missing={missing} extra={extra}")

        # 2) validar times/duplicados por día (aunque enabled=false, pueden quedar guardados)
        for d in self.days:
            seen = set()
            for slot in d.timeSlots:
                t = slot.time

                # HH:mm fuerte
                if len(t) != 5 or t[2] != ":":
                    raise ValueError(f"Invalid time '{t}' in {d.day}. Use HH:MM.")
                hh_s, mm_s = t.split(":")
                if not (hh_s.isdigit() and mm_s.isdigit()):
                    raise ValueError(f"Invalid time '{t}' in {d.day}. Use numbers.")
                hh, mm = int(hh_s), int(mm_s)
                if hh < 0 or hh > 23 or mm < 0 or mm > 59:
                    raise ValueError(
                        f"Invalid time '{t}' in {d.day}. Hour 0-23, minute 0-59."
                    )
                if mm % 5 != 0:
                    raise ValueError(
                        f"Invalid time '{t}' in {d.day}. Minutes must be divisible by 5."
                    )

                if t in seen:
                    raise ValueError(f"Duplicate time '{t}' in {d.day}.")
                seen.add(t)

        return self


class HospitalAvailabilityOut(HospitalAvailabilityIn):
    # ✅ response / db payload: incluye id_hospital (lo setea el back con uid)
    id_hospital: str
