from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.api.v1.services.blood_bank_service import get_or_create_blood_bank_service
from app.api.v1.services.appointment_service import search_appointments_by_range_service
from app.api.v1.services.hospital_request_service import get_hospital_requests_service

BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def _format_date_ddmmyyyy(value: str) -> str:
    try:
        d = datetime.fromisoformat(value).date()
        return d.strftime("%d/%m/%Y")
    except Exception:
        return value or ""


def get_home_summary_service(hospital_id: str) -> dict:
    today = datetime.now(BA_TZ).date()
    tomorrow = today + timedelta(days=1)

    # 1) Blood bank
    blood_bank = get_or_create_blood_bank_service(hospital_id)
    stocks = blood_bank.stocks_units or {}
    thresholds = blood_bank.thresholds_units or {}

    total_units = sum(int(v or 0) for v in stocks.values())

    critical_groups_count = 0
    for blood_type, stock_value in stocks.items():
        threshold_value = int(thresholds.get(blood_type, 0) or 0)
        if int(stock_value or 0) < threshold_value:
            critical_groups_count += 1

    # 2) Appointments hoy y mañana
    appointments_raw = search_appointments_by_range_service(hospital_id, today, tomorrow)

    appointments = []
    appointments_today_count = 0

    for appt in appointments_raw:
        date_local = appt.get("date_local") or ""
        status = (appt.get("status") or "").upper()

        if date_local == today.isoformat() and status in {"PROGRAMADO", "CONFIRMADO"}:
            appointments_today_count += 1

        appointments.append({
            "time_local": appt.get("time_local") or "",
            "donation_type": appt.get("donation_type") or "",
            "status": appt.get("status") or "",
        })

    appointments.sort(key=lambda x: x.get("time_local", ""))

    # 3) Hospital requests
    requests_raw = get_hospital_requests_service(hospital_id)

    urgent_active_count = 0
    active_requests = []

    for req in requests_raw:
        raw_status = (req.get("status") or "").upper()
        raw_priority = (req.get("priority") or "").upper()

        if raw_status == "ACTIVO" and raw_priority in {"URGENTE", "CRITICA"}:
            urgent_active_count += 1

        active_requests.append({
            "date": _format_date_ddmmyyyy((req.get("datetime_local") or "").split("T")[0]),
            "hospital_unit": req.get("hospital_unit") or "",
            "component": req.get("component") or "",
            "blood_group": req.get("blood_group") or "",
            "requested_units": req.get("requested_units") or 0,
            "priority": req.get("priority") or "",
            "status": req.get("status") or "",
        })

    return {
        "stocks": stocks,
        "thresholds": thresholds,
        "kpis": {
            "totalUnits": total_units,
            "urgentActive": urgent_active_count,
            "appointmentsToday": appointments_today_count,
            "criticalGroupsCount": critical_groups_count,
        },
        "appointments": appointments,
        "activeRequests": active_requests,
    }