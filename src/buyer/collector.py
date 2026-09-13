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


def run_collection(store, search_id, scraper_manager, on_progress=None, should_cancel=None, batch_size=5):
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
    cancelled = False
    checked = 0
    saved_total = 0
    batch_size = max(1, int(batch_size))

    for portal in portals:
        if should_cancel and should_cancel():
            cancelled = True
            break

        pending = []
        saved_for_portal = 0
        streamed = False

        def flush():
            nonlocal pending, saved_for_portal, saved_total
            for raw in pending:
                try:
                    store.save_listing(run_id, _to_canonical(raw, source=portal))
                    saved_for_portal += 1
                    saved_total += 1
                except ValueError:
                    pass
            pending = []
            if on_progress:
                on_progress({"portal": portal, "checked": checked, "saved": saved_total})

        def on_listing(raw):
            nonlocal streamed
            streamed = True
            pending.append(raw)

        def on_checked():
            nonlocal checked, streamed
            streamed = True
            checked += 1
            if checked % batch_size == 0:
                flush()

        try:
            raw_listings = scraper_manager.scrape_website(
                website=portal,
                max_price=max_price,
                min_surface=min_surface,
                epc_scores=epc_labels,
                postal_codes=postal_codes,
                max_pages=max_pages,
                on_listing=on_listing,
                on_checked=on_checked,
                should_cancel=should_cancel,
            )
            if not streamed:
                for raw in raw_listings:
                    on_listing(raw)
                    on_checked()
            if pending:
                flush()
            if should_cancel and should_cancel():
                cancelled = True
                store.record_source_result(run_id, portal, "cancelled", saved_for_portal)
                break
            store.record_source_result(run_id, portal, "ok", saved_for_portal)
        except Exception as exc:
            overall_ok = False
            store.record_source_result(run_id, portal, "error", saved_for_portal, str(exc))

    if cancelled:
        store.finish_run(run_id, "cancelled")
    else:
        store.finish_run(run_id, "ok" if overall_ok else "partial")
    return run_id
