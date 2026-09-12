"""Udaljenost i smjer između dvije države. Čista matematika."""
import math

EARTH_RADIUS_KM = 6371
ARROWS = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"]


def distance_km(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return round(EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a)))


def arrow(lat1, lon1, lat2, lon2):
    """Strelica koja pokazuje od pogođene države prema traženoj."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    y = math.sin(d_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    degrees = (math.degrees(math.atan2(y, x)) + 360) % 360
    # 8 smjerova, svaki pokriva 45°, pa zaokružujemo na najbliži.
    return ARROWS[round(degrees / 45) % 8]
