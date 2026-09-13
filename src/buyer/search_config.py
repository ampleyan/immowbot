AVAILABLE_PORTALS = ("immoweb", "immoscoop", "zimmo", "realo", "immovlan")
DEFAULT_SCORE_WEIGHTS = {"price": 30, "surface_area": 25, "bedrooms": 15, "epc": 20, "completeness": 10}

DEFAULT_HOME_SEARCH = {
    "postcodes": ["2000", "2018"],
    "property_types": ["house", "apartment"],
    "min_price": None,
    "max_price": 385000,
    "min_surface_area": 80,
    "min_bedrooms": 2,
    "outdoor_features": [],
    "building_age": "any",
    "min_construction_year": None,
    "max_construction_year": None,
    "scrape_mode": "all",
    "score_weights": dict(DEFAULT_SCORE_WEIGHTS),
    "epc_labels": ["A", "B", "C"],
    "portals": list(AVAILABLE_PORTALS),
    "max_pages": 5,
    "starting_capital": 50000,
    "emergency_reserve": 10000,
    "monthly_net_income": 4000,
    "monthly_debt_payments": 0,
    "interest_rate": 0.035,
    "loan_term_years": 25,
    "debt_service_ratio": 0.4,
    "loan_to_value": 0.9,
    "registration_tax_rate": 0.02,
    "vat_rate": 0.21,
    "notary_rate": 0.01,
    "mortgage_rate": 0.01,
    "bank_costs": 1000,
    "new_build_override": None,
}

DEFAULT_INVESTMENT_SEARCH = {
    **DEFAULT_HOME_SEARCH,
    "postcodes": list(DEFAULT_HOME_SEARCH["postcodes"]),
    "property_types": list(DEFAULT_HOME_SEARCH["property_types"]),
    "epc_labels": list(DEFAULT_HOME_SEARCH["epc_labels"]),
    "portals": list(DEFAULT_HOME_SEARCH["portals"]),
}


def normalize_search_config(data):
    config = dict(data)
    config["postcodes"] = list(dict.fromkeys(str(v).strip() for v in data.get("postcodes", [])))
    config["property_types"] = list(dict.fromkeys(str(v).strip().lower() for v in data.get("property_types", [])))
    config["epc_labels"] = list(dict.fromkeys(str(v).strip().upper() for v in data.get("epc_labels", [])))
    config["portals"] = list(dict.fromkeys(str(v).strip().lower() for v in data.get("portals", [])))
    config["outdoor_features"] = list(dict.fromkeys(str(v).strip().lower() for v in data.get("outdoor_features", [])))
    config["building_age"] = str(data.get("building_age", "any")).strip().lower()
    config["scrape_mode"] = str(data.get("scrape_mode", "all")).strip().lower()
    config["score_weights"] = {key: int(value) for key, value in dict(data.get("score_weights", DEFAULT_SCORE_WEIGHTS)).items()}
    for key in ("min_price", "max_price", "min_surface_area", "min_bedrooms", "min_construction_year", "max_construction_year", "max_pages", "starting_capital", "emergency_reserve", "monthly_net_income", "monthly_debt_payments", "loan_term_years", "bank_costs"):
        value = data.get(key)
        config[key] = None if value in (None, "") else int(value)
    for key in ("interest_rate", "debt_service_ratio", "loan_to_value", "registration_tax_rate", "vat_rate", "notary_rate", "mortgage_rate"):
        config[key] = float(data.get(key, DEFAULT_HOME_SEARCH[key]))
    if data.get("new_build_override") not in (None, "", True, False):
        raise ValueError("new_build_override must be true, false, or unset")
    config["new_build_override"] = data.get("new_build_override")
    if not config["postcodes"] or any(len(v) != 4 or not v.isdigit() for v in config["postcodes"]):
        raise ValueError("postcodes must contain four-digit Belgian postcodes")
    if not config["property_types"]:
        raise ValueError("property_types cannot be empty")
    if not config["portals"] or any(v not in AVAILABLE_PORTALS for v in config["portals"]):
        raise ValueError("portals must contain supported portal names")
    if any(v not in {"terrace", "garden"} for v in config["outdoor_features"]):
        raise ValueError("outdoor_features must contain terrace or garden")
    if config["building_age"] not in {"any", "project", "old"}:
        raise ValueError("building_age must be any, project, or old")
    if config["scrape_mode"] not in {"all", "delta"}:
        raise ValueError("scrape_mode must be all or delta")
    if set(config["score_weights"]) != set(DEFAULT_SCORE_WEIGHTS) or any(value < 0 for value in config["score_weights"].values()) or sum(config["score_weights"].values()) != 100:
        raise ValueError("score_weights must contain the five score parameters and total 100")
    if config["max_pages"] is None or config["max_pages"] < 1:
        raise ValueError("max_pages must be at least 1")
    for key in ("min_price", "max_price", "min_surface_area", "min_bedrooms", "min_construction_year", "max_construction_year"):
        if config[key] is not None and config[key] < 0:
            raise ValueError(f"{key} cannot be negative")
    if config["min_price"] is not None and config["max_price"] is not None and config["min_price"] > config["max_price"]:
        raise ValueError("min_price cannot exceed max_price")
    if config["min_construction_year"] is not None and config["max_construction_year"] is not None and config["min_construction_year"] > config["max_construction_year"]:
        raise ValueError("min_construction_year cannot exceed max_construction_year")
    return config
