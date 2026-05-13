RED_BLOOD_CELL_COMPATIBILITY = {
    "O-": {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"},
    "O+": {"O+", "A+", "B+", "AB+"},
    "A-": {"A-", "A+", "AB-", "AB+"},
    "A+": {"A+", "AB+"},
    "B-": {"B-", "B+", "AB-", "AB+"},
    "B+": {"B+", "AB+"},
    "AB-": {"AB-", "AB+"},
    "AB+": {"AB+"},
}


def can_donate_to_request(donor_blood_group: str, request_blood_group: str, component: str) -> bool:
    donor_bg = (donor_blood_group or "").strip().upper()
    req_bg = (request_blood_group or "").strip().upper()
    comp = (component or "").strip().upper()

    if not donor_bg or not req_bg:
        return False

    if comp == "SANGRE":
        return req_bg in RED_BLOOD_CELL_COMPATIBILITY.get(donor_bg, set())

    return donor_bg == req_bg


def is_exact_blood_match(donor_blood_group: str, request_blood_group: str) -> bool:
    donor_bg = (donor_blood_group or "").strip().upper()
    req_bg = (request_blood_group or "").strip().upper()
    if not donor_bg or not req_bg:
        return False
    return donor_bg == req_bg