from statistics import median

EPC_FACTOR = {
    "A++": 1.0,
    "A+": 1.0,
    "A": 1.0,
    "B": 0.7,
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
    return min(max((value - minimum) / minimum, 0.0), 1.0)


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


def passes_hard_filters(listing, config):
    required = ("postcode", "property_type", "price", "surface_area", "bedrooms", "epc_score")
    if any(listing.get(key) in (None, "") for key in required):
        return False
    construction_year = listing.get("construction_year")
    if config.get("min_construction_year") is not None and (construction_year is None or construction_year < config["min_construction_year"]):
        return False
    if config.get("max_construction_year") is not None and (construction_year is None or construction_year > config["max_construction_year"]):
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
    if not passes_hard_filters(listing, config):
        return {"score": None, "components": {}, "exclusions": ["hard_filters"]}
    components = {
        "price": 30 * _price_headroom(listing["price"], config["max_price"]),
        "surface_area": 25 * _ratio_above_minimum(listing["surface_area"], config["min_surface_area"]),
        "bedrooms": 15 * _ratio_above_minimum(listing["bedrooms"], config["min_bedrooms"]),
        "epc": 20 * EPC_FACTOR[_epc_label(listing["epc_score"])],
        "completeness": 10 * _completeness(listing),
    }
    components = {key: round(value, 2) for key, value in components.items()}
    return {"score": round(sum(components.values()), 2), "components": components, "exclusions": []}


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
