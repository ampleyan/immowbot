from datetime import datetime, timedelta, timezone


BUILTIN_SMART_LISTS = (
    ("Contact now", {"score_min": 75, "affordability": "affordable"}),
    ("Affordable", {"affordability": "affordable"}),
    ("Cash shortfall", {"affordability": "shortfall"}),
    ("New this week", {"first_seen_days": 7}),
    ("Terrace or garden", {"outdoor_features": ["terrace", "garden"]}),
    ("Needs review", {"needs_review": True}),
    ("By postcode", {"group_by": "postcode"}),
    ("By portal", {"group_by": "portal"}),
)


def matches_rule(listing, rule, score=None, purchase=None, now=None):
    rule = rule or {}
    if rule.get("score_min") is not None and (score is None or score < rule["score_min"]):
        return False
    if rule.get("score_max") is not None and (score is None or score > rule["score_max"]):
        return False
    if rule.get("affordability"):
        state = "unknown"
        if purchase and purchase.get("available"):
            state = "affordable" if purchase.get("cash_surplus", -1) >= 0 else "shortfall"
        if state != rule["affordability"]:
            return False
    if rule.get("first_seen_days") is not None:
        raw = listing.get("_first_seen_at") or listing.get("first_seen_at")
        if not raw:
            return False
        try:
            seen = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            seen = seen if seen.tzinfo else seen.replace(tzinfo=timezone.utc)
            reference = now or datetime.now(timezone.utc)
            if reference - seen > timedelta(days=float(rule["first_seen_days"])):
                return False
        except (TypeError, ValueError):
            return False
    if rule.get("postcodes") and str(listing.get("postcode", "")) not in {str(v) for v in rule["postcodes"]}:
        return False
    if rule.get("portals") and str(listing.get("source", "")).lower() not in {str(v).lower() for v in rule["portals"]}:
        return False
    if rule.get("property_types") and str(listing.get("property_type", "")).lower() not in {str(v).lower() for v in rule["property_types"]}:
        return False
    outdoor = rule.get("outdoor_features", [])
    if outdoor and not any(listing.get("outdoor_" + feature) or (feature == "terrace" and listing.get("outdoor_surface")) for feature in outdoor):
        return False
    if rule.get("statuses") and listing.get("workflow_status", "new") not in set(rule["statuses"]):
        return False
    if rule.get("needs_review"):
        missing_location = listing.get("latitude") in (None, "") or listing.get("longitude") in (None, "")
        if not (score is None or (score is not None and score < 55) or not purchase or not purchase.get("available") or missing_location):
            return False
    return True
