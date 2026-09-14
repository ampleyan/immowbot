from math import hypot
import re


def _address(listing):
    text = " ".join(str(listing.get(key, "")) for key in ("address", "street", "house_number", "city", "postcode", "location", "name"))
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _normalized(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def duplicate_groups(listings):
    groups = []
    used = set()
    for index, listing in enumerate(listings):
        if index in used:
            continue
        matches = [listing]
        signals = []
        for other_index in range(index + 1, len(listings)):
            other = listings[other_index]
            same_address = bool(_address(listing) and _address(listing) == _address(other))
            same_postcode = bool(_normalized(listing.get("postcode")) and _normalized(listing.get("postcode")) == _normalized(other.get("postcode")))
            close_coords = all(value not in (None, "") for value in (listing.get("latitude"), listing.get("longitude"), other.get("latitude"), other.get("longitude"))) and hypot(float(listing["latitude"]) - float(other["latitude"]), float(listing["longitude"]) - float(other["longitude"])) < 0.001
            same_price = listing.get("price") not in (None, "") and other.get("price") not in (None, "") and listing.get("price") == other.get("price")
            same_surface = listing.get("surface_area") and other.get("surface_area") and abs(listing["surface_area"] - other["surface_area"]) <= max(5, listing["surface_area"] * 0.05)
            same_bedrooms = listing.get("bedrooms") not in (None, "") and other.get("bedrooms") not in (None, "") and listing.get("bedrooms") == other.get("bedrooms")
            matching_details = same_address and same_postcode and same_price and same_surface
            if matching_details:
                matches.append(other)
                used.add(other_index)
                signals.append({"source": other.get("source"), "signals": [name for name, value in (("address", same_address), ("postcode", same_postcode), ("coordinates", close_coords), ("price", same_price), ("surface", same_surface), ("bedrooms", same_bedrooms)) if value]})
        if len(matches) > 1:
            confidence = "high" if any(item["signals"] and ("address" in item["signals"] or len(item["signals"]) >= 3) for item in signals) else "medium"
            groups.append({"canonical": matches[0], "offers": matches, "confidence": confidence, "signals": signals})
        used.add(index)
    return groups
