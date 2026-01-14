import requests
from typing import Optional, Dict

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

def geocode_address_nominatim(address_text: str) -> Optional[Dict[str, float]]:
    params = {
        "q": f"{address_text}, Argentina",
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "vitflow/1.0"
    }

    r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()

    if not data:
        return None

    return {"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"])}
