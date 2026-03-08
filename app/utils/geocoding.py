import os
import requests
from typing import Optional, Dict

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
API_KEY = os.getenv("GOOGLE_GEOCODING_API_KEY")


def geocode_address_google(address_text: str) -> Optional[Dict[str, float]]:
    params = {
        "address": f"{address_text}, Argentina",
        "key": API_KEY,
        "region": "ar",
    }

    headers = {
        "User-Agent": "vitflow/1.0"
    }

    r = requests.get(GOOGLE_GEOCODE_URL, params=params, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()

    if data.get("status") != "OK":
        return None

    location = data["results"][0]["geometry"]["location"]

    return {
        "lat": float(location["lat"]),
        "lng": float(location["lng"]),
    }