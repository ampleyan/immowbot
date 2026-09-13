def calculate_purchase_estimate(listing, config):
    price = listing.get("price")
    if not price or price <= 0:
        return {"available": False, "missing": ["price"]}

    income = config.get("monthly_net_income")
    debt = config.get("monthly_debt_payments")
    if income is None or debt is None:
        return {"available": False, "missing": ["monthly income and debt payments"]}

    is_new_build = config.get("new_build_override")
    if is_new_build is None:
        is_new_build = config.get("building_age") == "project" or bool(listing.get("construction_year") and listing["construction_year"] >= 2024)
    tax_rate = config.get("vat_rate", 0.21) if is_new_build else config.get("registration_tax_rate", 0.02)
    tax = price * tax_rate
    notary = price * config.get("notary_rate", 0.01)
    mortgage_cost = price * config.get("mortgage_rate", 0.01)
    bank_costs = config.get("bank_costs", 1000)
    total_cost = price + tax + notary + mortgage_cost + bank_costs

    monthly_rate = config.get("interest_rate", 0.035) / 12
    months = config.get("loan_term_years", 25) * 12
    payment_capacity = max(0, income * config.get("debt_service_ratio", 0.4) - debt)
    if monthly_rate > 0:
        affordable_loan = payment_capacity * (1 - (1 + monthly_rate) ** -months) / monthly_rate
    else:
        affordable_loan = payment_capacity * months
    ltv_loan = price * config.get("loan_to_value", 0.9)
    loan = max(0, min(affordable_loan, ltv_loan))
    available_cash = max(0, config.get("starting_capital", 0) - config.get("emergency_reserve", 0))
    required_cash = max(0, total_cost - loan)
    return {
        "available": True,
        "is_new_build": bool(is_new_build),
        "price": round(price),
        "tax": round(tax),
        "notary": round(notary),
        "mortgage_cost": round(mortgage_cost),
        "bank_costs": round(bank_costs),
        "total_cost": round(total_cost),
        "estimated_loan": round(loan),
        "required_cash": round(required_cash),
        "available_cash": round(available_cash),
        "cash_surplus": round(available_cash - required_cash),
    }
