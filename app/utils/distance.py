from math import radians, sin, cos, sqrt, atan2


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Devuelve la distancia en kilómetros entre dos puntos geográficos.
    """
    r = 6371.0  # radio de la Tierra en km

    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return r * c