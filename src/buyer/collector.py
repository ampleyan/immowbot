from src.buyer.property_store import PropertyStore

_CANONICAL_FIELDS = frozenset((
    "source", "source_listing_id", "url", "transaction_type",
    "price", "postcode", "property_type", "surface_area", "bedrooms", "epc_score",
))


def _to_canonical(raw, source, transaction_type="sale"):
    listing_id = str(raw.get("id") or "")
    if not listing_id:
        listing_id = raw.get("url", "")
    extra = {k: v for k, v in raw.items() if k not in _CANONICAL_FIELDS and k != "source_website"}
    return {
        "source": source,
        "source_listing_id": listing_id,
        "url": raw.get("url", ""),
        "transaction_type": transaction_type,
        "price": raw.get("price"),
        "postcode": str(raw.get("postcode") or ""),
        "property_type": str(raw.get("property_type") or "").lower(),
        "surface_area": raw.get("surface_area"),
        "bedrooms": raw.get("bedrooms"),
        "epc_score": raw.get("epc_score"),
        **extra,
    }


def run_collection(store, search_id, scraper_manager):
    search = store.get_search(search_id)
    config = search["config"]
    run_id = store.start_run(search_id)

    portals = config.get("portals", [])
    max_pages = config.get("max_pages", 5)
    postal_codes = config.get("postcodes", [])
    max_price = config.get("max_price")
    min_surface = config.get("min_surface_area")
    epc_labels = config.get("epc_labels")

    overall_ok = True

    for portal in portals:
        try:
            raw_listings = scraper_manager.scrape_website(
                website=portal,
                max_price=max_price,
                min_surface=min_surface,
                epc_scores=epc_labels,
                postal_codes=postal_codes,
                max_pages=max_pages,
            )
            saved = 0
            skipped = 0
            for raw in raw_listings:
                try:
                    listing = _to_canonical(raw, source=portal)
                    store.save_listing(run_id, listing)
                    saved += 1
                except ValueError:
                    skipped += 1
            store.record_source_result(run_id, portal, "ok", saved)
        except Exception as exc:
            overall_ok = False
            store.record_source_result(run_id, portal, "error", 0, str(exc))

    store.finish_run(run_id, "ok" if overall_ok else "partial")
    return run_id
