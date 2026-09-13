from math import asin, cos, radians, sin, sqrt


def commute_estimate(listing, destinations):
    lat, lon = listing.get("latitude"), listing.get("longitude")
    if lat in (None, "") or lon in (None, ""):
        return {"available": False, "reason": "listing coordinates unavailable", "score": None, "destinations": []}
    results = []
    for destination in destinations or []:
        if not destination.get("enabled", True) or destination.get("latitude") in (None, "") or destination.get("longitude") in (None, ""):
            continue
        distance = _distance_km(float(lat), float(lon), float(destination["latitude"]), float(destination["longitude"]))
        minutes = round(distance / ({"walking": 5, "cycling": 15, "driving": 35, "transit": 25}.get(destination.get("mode", "driving"), 35) / 60))
        maximum = float(destination.get("max_minutes") or 60)
        results.append({"name": destination.get("name") or "Destination", "distance_km": round(distance, 1), "minutes": minutes, "mode": destination.get("mode", "driving"), "score": round(max(0, min(100, (1 - minutes / maximum) * 100)), 1)})
    if not results:
        return {"available": False, "reason": "no configured destinations", "score": None, "destinations": []}
    return {"available": True, "score": round(sum(item["score"] for item in results) / len(results), 1), "destinations": results}


def _distance_km(lat1, lon1, lat2, lon2):
    earth_radius = 6371
    d_lat, d_lon = radians(lat2 - lat1), radians(lon2 - lon1)
    value = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return earth_radius * 2 * asin(sqrt(value))
