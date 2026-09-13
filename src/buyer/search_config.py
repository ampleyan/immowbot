AVAILABLE_PORTALS = ("immoweb", "immoscoop", "zimmo", "realo", "immovlan")

DEFAULT_HOME_SEARCH = {
    "postcodes": ["2000", "2018"],
    "property_types": ["house", "apartment"],
    "min_price": None,
    "max_price": 385000,
    "min_surface_area": 80,
    "min_bedrooms": 2,
    "epc_labels": ["A", "B", "C"],
    "portals": list(AVAILABLE_PORTALS),
    "max_pages": 5,
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
    for key in ("min_price", "max_price", "min_surface_area", "min_bedrooms", "max_pages"):
        value = data.get(key)
        config[key] = None if value in (None, "") else int(value)
    if not config["postcodes"] or any(len(v) != 4 or not v.isdigit() for v in config["postcodes"]):
        raise ValueError("postcodes must contain four-digit Belgian postcodes")
    if not config["property_types"]:
        raise ValueError("property_types cannot be empty")
    if not config["portals"] or any(v not in AVAILABLE_PORTALS for v in config["portals"]):
        raise ValueError("portals must contain supported portal names")
    if config["max_pages"] is None or config["max_pages"] < 1:
        raise ValueError("max_pages must be at least 1")
    for key in ("min_price", "max_price", "min_surface_area", "min_bedrooms"):
        if config[key] is not None and config[key] < 0:
            raise ValueError(f"{key} cannot be negative")
    if config["min_price"] is not None and config["max_price"] is not None and config["min_price"] > config["max_price"]:
        raise ValueError("min_price cannot exceed max_price")
    return config
