from statistics import median

EPC_FACTOR = {
    "A++": 1.0,
    "A+": 1.0,
    "A": 1.0,
    "B": 0.85,
    "C": 0.4,
    "D": 0.25,
    "E": 0.15,
    "F": 0.05,
    "G": 0.0,
}
COMPLETENESS_FIELDS = ("price", "postcode", "property_type", "surface_area", "bedrooms", "epc_score", "url")


def _ratio_above_minimum(value, minimum):
    if not minimum:
        return 1.0
    return min(max(value / (minimum * 1.25), 0.0), 1.0)


def _price_headroom(price, maximum):
    if not maximum:
        return 1.0
    return min(max((maximum - price) / maximum, 0.0), 1.0)


def _completeness(listing):
    present = sum(listing.get(key) not in (None, "") for key in COMPLETENESS_FIELDS)
    return present / len(COMPLETENESS_FIELDS)


def _epc_label(value):
    text = str(value or "").strip().upper()
    return next((label for label in ("A++", "A+", "A", "B", "C", "D", "E", "F", "G") if text.startswith(label)), "")


def _is_project(listing):
    text = " ".join(str(listing.get(key, "")) for key in ("property_type", "building_state", "title", "name")).lower()
    return any(term in text for term in ("project", "new build", "newly built", "nieuwbouw", "neuf"))


def _outdoor_bonus(listing):
    return 5 if listing.get("outdoor_terrace") or listing.get("outdoor_garden") or listing.get("outdoor_surface") else 0


def _has_parking(listing):
    details = listing.get("all_property_details") or {}
    if details.get("Garage") or details.get("Parking indoor") or details.get("Parking outdoor") or details.get("Parking closed box"):
        return True
    return bool(listing.get("garage") or listing.get("parking"))


def _parking_bonus(listing):
    return 5 if _has_parking(listing) else 0


def _price_per_sqm_bonus(listing):
    price = listing.get("price")
    surface = listing.get("surface_area")
    avg = listing.get("_postcode_avg_price_per_sqm")
    if not price or not surface or not avg or surface <= 0:
        return 0
    ratio = (avg - price / surface) / avg
    return max(0, min(10, round(ratio * 20, 2)))


def _price_reduced_bonus(listing):
    return 5 if listing.get("_price_reduced") else 0


def _days_on_market_bonus(listing):
    from datetime import datetime, timezone
    first_seen = listing.get("_first_seen_at")
    if not first_seen:
        return 0
    try:
        seen_dt = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - seen_dt).days
    except Exception:
        return 0
    if days < 14:
        return 5
    if days > 90:
        return -5
    return 0


def _tenant_penalty(listing):
    return -10 if listing.get("has_tenant") else 0


def _monthly_charges_penalty(listing):
    charges = listing.get("monthly_charges")
    if not charges:
        return 0
    try:
        charges = float(charges)
    except (TypeError, ValueError):
        return 0
    if charges <= 150:
        return 0
    return max(-10, -round((charges - 150) / 50, 2))


def passes_hard_filters(listing, config):
    required = ("postcode", "property_type", "price", "surface_area", "bedrooms", "epc_score")
    if any(listing.get(key) in (None, "") for key in required):
        return False
    construction_year = listing.get("construction_year")
    if config.get("min_construction_year") is not None and (construction_year is None or construction_year < config["min_construction_year"]):
        return False
    if config.get("max_construction_year") is not None and (construction_year is None or construction_year > config["max_construction_year"]):
        return False
    if config.get("exclude_tenants") and listing.get("has_tenant"):
        return False
    outdoor = config.get("outdoor_features", [])
    if "terrace" in outdoor and not (listing.get("outdoor_terrace") or listing.get("outdoor_surface")):
        return False
    if "garden" in outdoor and not listing.get("outdoor_garden"):
        return False
    if config.get("building_age") == "project" and not _is_project(listing):
        return False
    if config.get("building_age") == "old" and _is_project(listing):
        return False
    return (
        str(listing["postcode"]).strip() in {str(code).strip() for code in config["postcodes"]}
        and str(listing["property_type"]).lower() in config["property_types"]
        and (config["min_price"] is None or listing["price"] >= config["min_price"])
        and (config["max_price"] is None or listing["price"] <= config["max_price"])
        and (config["min_surface_area"] is None or listing["surface_area"] >= config["min_surface_area"])
        and (config["min_bedrooms"] is None or listing["bedrooms"] >= config["min_bedrooms"])
        and _epc_label(listing["epc_score"]) in config["epc_labels"]
    )


def calculate_home_score(listing, config):
    excluded = not passes_hard_filters(listing, config)
    try:
        components = {
            "price": config["score_weights"]["price"] * _price_headroom(listing.get("price") or 0, config["max_price"]),
            "surface_area": config["score_weights"]["surface_area"] * _ratio_above_minimum(listing.get("surface_area") or 0, config["min_surface_area"]),
            "bedrooms": config["score_weights"]["bedrooms"] * _ratio_above_minimum(listing.get("bedrooms") or 0, config["min_bedrooms"]),
            "epc": config["score_weights"]["epc"] * EPC_FACTOR.get(_epc_label(listing.get("epc_score")), 0),
            "completeness": config["score_weights"]["completeness"] * _completeness(listing),
            "outdoor": _outdoor_bonus(listing),
            "parking": _parking_bonus(listing),
            "price_per_sqm": _price_per_sqm_bonus(listing),
            "price_reduced": _price_reduced_bonus(listing),
            "days_on_market": _days_on_market_bonus(listing),
            "tenant": _tenant_penalty(listing),
            "monthly_charges": _monthly_charges_penalty(listing),
        }
        components = {key: round(value, 2) for key, value in components.items() if value != 0}
    except Exception:
        components = {}
    if excluded:
        return {"score": None, "components": components, "exclusions": ["hard_filters"]}
    return {"score": min(100, round(sum(components.values()), 2)), "components": components, "exclusions": []}


def select_rent_comparables(listing, rentals):
    lower_area = listing["surface_area"] * 0.8
    upper_area = listing["surface_area"] * 1.2
    return [
        rental for rental in rentals
        if rental.get("postcode") == listing.get("postcode")
        and rental.get("property_type") == listing.get("property_type")
        and rental.get("surface_area") is not None
        and lower_area <= rental["surface_area"] <= upper_area
        and rental.get("bedrooms") is not None
        and abs(rental["bedrooms"] - listing["bedrooms"]) <= 1
        and rental.get("price", 0) > 0
    ]


def calculate_investment_score(listing, config, rentals):
    if not passes_hard_filters(listing, config):
        return {"score": None, "components": {}, "exclusions": ["hard_filters"]}
    comparables = select_rent_comparables(listing, rentals)
    monthly_rent = median(item["price"] for item in comparables) if comparables else None
    gross_yield = monthly_rent * 12 / listing["price"] * 100 if monthly_rent is not None else None
    components = {
        "yield": round(50 * min(gross_yield / 6, 1), 2) if gross_yield is not None else 0,
        "epc": round(20 * EPC_FACTOR[_epc_label(listing["epc_score"])], 2),
        "price": round(15 * _price_headroom(listing["price"], config["max_price"]), 2),
        "completeness": round(15 * _completeness(listing), 2),
        "comparable_count": len(comparables),
        "median_monthly_rent": monthly_rent,
        "gross_yield_percent": round(gross_yield, 2) if gross_yield is not None else None,
    }
    scored_components = ("yield", "epc", "price", "completeness")
    return {"score": round(sum(components[key] for key in scored_components), 2), "components": components, "exclusions": []}
