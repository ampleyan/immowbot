from src.buyer.property_store import PropertyStore
from src.translator import PropertyTranslator
from src.buyer.duplicate_detection import duplicate_groups

_translator = PropertyTranslator()

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


def _merge_high_confidence_duplicates(store):
    for group in duplicate_groups(store.latest_listings("sale")):
        offers = group["offers"]
        if group["confidence"] != "high" or len(offers) != 2 or len({offer.get("source") for offer in offers}) < 2:
            continue
        keep = max(offers, key=lambda offer: sum(value not in (None, "", [], {}) for value in offer.values()))
        merged = dict(keep)
        merged_images = []
        for offer in offers:
            for image in offer.get("images") or []:
                if image and image not in merged_images:
                    merged_images.append(image)
            for key, value in offer.items():
                if key not in merged or merged[key] in (None, "", [], {}):
                    merged[key] = value
        if merged_images:
            merged["images"] = merged_images
            merged["image_url_1"] = merged_images[0]
            merged["image_url_2"] = merged_images[1] if len(merged_images) > 1 else None
        alternate_sources = [
            {"source": offer.get("source"), "source_listing_id": str(offer.get("source_listing_id")), "url": offer.get("url")}
            for offer in offers if offer is not keep
        ]
        if alternate_sources:
            merged["alternate_sources"] = alternate_sources
        store.merge_listing_payload(keep["source"], keep["source_listing_id"], merged)
        for offer in offers:
            if offer is not keep:
                store.delete_listing(offer.get("source"), offer.get("source_listing_id"))


DUTCH_MARKERS = (
    "slaapkamer", "woonkamer", "badkamer", "verdieping", "instapklaar",
    "gelegen", "beschikt", "woning", "keuken", "bewonen", "tuin",
    "appartement", "slaapkamers", "om zelf te", "te koop",
)

def _needs_translation(listing):
    description = listing.get("description")
    if not description:
        return False
    lang = listing.get("description_language") or ""
    if lang == "en":
        return False
    english = listing.get("description_english") or ""
    if not english or english == description:
        return True
    en_lower = english.lower()
    if any(p in en_lower for p in (
        "here's the translation", "here is the translation", "translation:"
    )):
        return True
    if any(p in en_lower for p in DUTCH_MARKERS):
        return True
    return False


def translate_listing(store, source, source_listing_id):
    listing = store.get_listing(source, source_listing_id)
    if not listing or not _needs_translation(listing):
        return False
    result = _translator.translate_property_description(listing["description"], target_language="en")
    english = result.get("translated") or ""
    if not english:
        return False
    store.update_translation(source, source_listing_id, english, result.get("detected_language"))
    return True


def _translate_scraped(store, scraped, on_progress=None):
    for i, (source, source_listing_id) in enumerate(scraped):
        if on_progress:
            on_progress(i, len(scraped), source_listing_id)
        translate_listing(store, source, source_listing_id)
    if on_progress:
        on_progress(len(scraped), len(scraped), "")


def run_collection(store, search_id, scraper_manager, on_progress=None, should_cancel=None, batch_size=5, on_translate_progress=None):
    search = store.get_search(search_id)
    config = search["config"]
    run_id = store.start_run(search_id)

    portals = config.get("portals", [])
    max_pages = config.get("max_pages", 5)
    postal_codes = config.get("postcodes", [])
    max_price = config.get("max_price")
    min_surface = config.get("min_surface_area")
    epc_labels = config.get("epc_labels")
    scrape_mode = config.get("scrape_mode", "all")
    if scrape_mode == "delta":
        max_pages = min(max_pages, 3)

    overall_ok = True
    cancelled = False
    checked = 0
    saved_total = 0
    batch_size = max(1, int(batch_size))
    scraped_this_run = []

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
                    canonical = _to_canonical(raw, source=portal)
                    description = canonical.get("description")
                    if description:
                        existing = store.get_listing(canonical["source"], canonical["source_listing_id"])
                        if existing and existing.get("description") == description and existing.get("description_english") and not _needs_translation(existing):
                            canonical["description_english"] = existing["description_english"]
                            canonical["description_language"] = existing.get("description_language")
                        else:
                            canonical["description_english"] = ""
                    store.save_listing(run_id, canonical)
                    scraped_this_run.append((canonical["source"], str(canonical["source_listing_id"])))
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
            try:
                scraper = scraper_manager.get_scraper(portal)
                if scrape_mode == "delta":
                    can_enrich_galleries = callable(getattr(scraper, "is_property_already_scraped", None))
                    known_urls = set()
                    needs_gallery = 0
                    for listing in store.latest_listings("sale"):
                        if listing.get("source") != portal or not listing.get("url"):
                            continue
                        images = listing.get("images")
                        if not can_enrich_galleries or (isinstance(images, list) and images):
                            known_urls.add(listing["url"])
                        else:
                            needs_gallery += 1
                    scraper.existing_properties = known_urls
                    print(f"[collector] {portal}: delta mode, {len(known_urls)} complete listings skipped, {needs_gallery} listings queued for gallery enrichment")
                else:
                    scraper.existing_properties.clear()
            except (AttributeError, ValueError):
                pass

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
        if config.get("translate_to_english", True):
            _translate_scraped(store, scraped_this_run, on_progress=on_translate_progress)
        _merge_high_confidence_duplicates(store)
        store.finish_run(run_id, "ok" if overall_ok else "partial")
    return run_id


def run_selected_collection(store, search_id, scraper_manager, selections, on_progress=None, should_cancel=None, on_translate_progress=None):
    search = store.get_search(search_id)
    config = search["config"]
    run_id = store.start_run(search_id)
    grouped = {}
    for selection in selections:
        grouped.setdefault(selection["source"], []).append(selection)
    checked = 0
    saved_total = 0
    cancelled = False
    overall_ok = True
    scraped_this_run = []

    for source, source_selections in grouped.items():
        saved_for_source = 0

        def on_listing(raw, current_source=source):
            nonlocal saved_for_source, saved_total
            canonical = _to_canonical(raw, source=current_source)
            description = canonical.get("description")
            if description:
                existing = store.get_listing(canonical["source"], canonical["source_listing_id"])
                if existing and existing.get("description") == description and not _needs_translation(existing):
                    canonical["description_english"] = existing["description_english"]
                    canonical["description_language"] = existing.get("description_language")
                else:
                    canonical["description_english"] = ""
            store.save_listing(run_id, canonical)
            scraped_this_run.append((canonical["source"], str(canonical["source_listing_id"])))
            saved_for_source += 1
            saved_total += 1

        def on_checked(current_source=source):
            nonlocal checked
            checked += 1
            if on_progress:
                on_progress({"portal": current_source, "checked": checked, "saved": saved_total})

        try:
            scraper_manager.scrape_selected_listings(
                source_selections,
                on_listing=on_listing,
                on_checked=on_checked,
                should_cancel=should_cancel,
            )
            if should_cancel and should_cancel():
                cancelled = True
                store.record_source_result(run_id, source, "cancelled", saved_for_source)
                break
            store.record_source_result(run_id, source, "ok", saved_for_source)
        except Exception as exc:
            overall_ok = False
            store.record_source_result(run_id, source, "error", saved_for_source, str(exc))

    if cancelled:
        store.finish_run(run_id, "cancelled")
    else:
        if config.get("translate_to_english", True):
            _translate_scraped(store, scraped_this_run, on_progress=on_translate_progress)
        _merge_high_confidence_duplicates(store)
        store.finish_run(run_id, "ok" if overall_ok else "partial")
    return run_id
