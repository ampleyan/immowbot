LABELS = {
    "price": "price",
    "surface_area": "surface",
    "bedrooms": "bedrooms",
    "epc": "energy rating",
    "completeness": "complete details",
}
MAXIMUMS = {"price": 30, "surface_area": 25, "bedrooms": 15, "epc": 20, "completeness": 10}


def explain_property(listing, score, components, exclusions, purchase):
    if exclusions:
        reasons = ", ".join(exclusions)
        return {"summary": "Excluded because it fails: " + reasons + ".", "strengths": [], "weaknesses": [reasons]}
    strengths = []
    weaknesses = []
    for key, value in sorted((components or {}).items(), key=lambda item: item[1], reverse=True):
        label = LABELS.get(key, key)
        ratio = value / MAXIMUMS.get(key, 1)
        if ratio >= 0.7:
            strengths.append(label)
        elif ratio < 0.45:
            weaknesses.append(label)
    if purchase and purchase.get("available"):
        finance = "affordable" if purchase.get("cash_surplus", -1) >= 0 else "a cash shortfall"
        finance_text = f"Purchase estimate shows {finance}."
    else:
        finance_text = "Purchase estimate is unavailable."
    summary = f"Current score: {round(score or 0)}/100. " + finance_text
    if strengths:
        summary += " Strong match on " + ", ".join(strengths[:3]) + "."
    if weaknesses:
        summary += " Weakness: " + ", ".join(weaknesses[:2]) + "."
    return {"summary": summary, "strengths": strengths[:3], "weaknesses": weaknesses[:3]}
