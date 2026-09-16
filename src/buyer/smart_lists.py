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
    ("★★★★★ Rated 5 stars", {"rating_min": 5, "rating_max": 5}),
    ("★★★★ Rated 4 stars", {"rating_min": 4, "rating_max": 4}),
)


def explain_rule_match(listing, rule, score=None, purchase=None, rating=None):
    reasons = []
    if rule.get("rating_min") is not None:
        reasons.append(f"rated {rating or 0} out of 5 stars")
    if rule.get("score_min") is not None:
        reasons.append(f"score {round(score or 0)}/100 meets the {rule['score_min']}+ threshold")
    if rule.get("affordability") == "affordable":
        reasons.append("purchase estimate is affordable")
    elif rule.get("affordability") == "shortfall":
        reasons.append("purchase estimate shows a cash shortfall")
    if rule.get("first_seen_days") is not None:
        reasons.append(f"added within the last {rule['first_seen_days']} days")
    if rule.get("outdoor_features"):
        features = [feature for feature in rule["outdoor_features"] if listing.get("outdoor_" + feature) or (feature == "terrace" and listing.get("outdoor_surface"))]
        reasons.append("has " + " or ".join(features))
    if rule.get("needs_review"):
        if score is None or score < 55:
            reasons.append("score is below the review threshold")
        if not purchase or not purchase.get("available"):
            reasons.append("finance estimate is unavailable")
        if listing.get("latitude") in (None, "") or listing.get("longitude") in (None, ""):
            reasons.append("location coordinates are missing")
    if rule.get("postcodes"):
        reasons.append("postcode matches the list")
    if rule.get("portals"):
        reasons.append("portal matches the list")
    if rule.get("property_types"):
        reasons.append("property type matches the list")
    return "Matched because " + "; ".join(reasons) + "." if reasons else "Matches this smart-list rule."


def matches_rule(listing, rule, score=None, purchase=None, now=None, rating=None):
    rule = rule or {}
    if rule.get("rating_min") is not None and (not rating or rating < rule["rating_min"]):
        return False
    if rule.get("rating_max") is not None and (not rating or rating > rule["rating_max"]):
        return False
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
