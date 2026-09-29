import re

from src.buyer.commute import commute_estimate
from src.buyer.duplicate_detection import duplicate_groups
from src.buyer.property_explanation import explain_property
from src.buyer.property_scoring import calculate_home_score
from src.buyer.purchase_calculator import calculate_purchase_estimate


PHONE_RE = re.compile(r'(?:\+32|0032|0)\s*\d[\d\s.\-/]{6,12}\d')
EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', re.IGNORECASE)


def extract_contact_from_listing(listing):
    text = ' '.join(filter(None, [
        listing.get('description') or '',
        listing.get('description_english') or '',
        str((listing.get('all_property_details') or {}).get('Description (Original)') or ''),
        str((listing.get('all_property_details') or {}).get('Description (English)') or ''),
    ]))
    phone = PHONE_RE.search(text)
    email = EMAIL_RE.search(text)
    return {
        'phone': re.sub(r'\s+', ' ', phone.group()).strip() if phone else None,
        'email': email.group().strip() if email else None,
    }


def _postcode_average_price_per_sqm(listings):
    prices_by_postcode = {}
    for listing in listings:
        postcode = listing.get('postcode')
        price = listing.get('price')
        surface = listing.get('surface_area')
        if postcode and price and surface and surface > 0:
            prices_by_postcode.setdefault(postcode, []).append(price / surface)
    return {
        postcode: sum(prices) / len(prices)
        for postcode, prices in prices_by_postcode.items()
    }


def read_listing_results(store, user_id, search_id, selected_keys=None):
    """Load and enrich full or selected Listing results while preserving each payload."""
    config = store.get_search(search_id)['config']
    all_listings = store.latest_listings('sale')
    postcode_averages = _postcode_average_price_per_sqm(all_listings)
    for listing in all_listings:
        listing['_postcode_avg_price_per_sqm'] = postcode_averages.get(listing.get('postcode'))

    full_read = selected_keys is None
    if full_read:
        listings = all_listings
        duplicate_keys = {
            (offer.get('source'), str(offer.get('source_listing_id', '')))
            for group in duplicate_groups(all_listings)
            for offer in group['offers']
        }
    else:
        selected_keys = set(selected_keys)
        if not selected_keys:
            return []
        listings = [
            listing for listing in all_listings
            if (listing.get('source'), str(listing.get('source_listing_id', ''))) in selected_keys
        ]
        duplicate_keys = set()

    all_notes = store.get_all_notes(user_id)
    listing_keys = [
        (listing.get('source', ''), str(listing.get('source_listing_id', '')))
        for listing in listings
    ]
    list_ids_by_key = store.get_property_list_ids_for_listings(user_id, listing_keys)
    workflows_by_key = store.get_workflows_for_listings(user_id, listing_keys)

    results = []
    for listing in listings:
        scored = calculate_home_score(listing, config)
        score = scored['score']
        if not full_read and score is None and scored.get('components'):
            score = min(100, round(sum(scored['components'].values()), 2))

        source = listing.get('source', '')
        source_listing_id = str(listing.get('source_listing_id', ''))
        key = (source, source_listing_id)
        purchase_estimate = calculate_purchase_estimate(listing, config)
        if full_read and (not listing.get('agent_phone') or not listing.get('agent_email')):
            extracted = extract_contact_from_listing(listing)
            if not listing.get('agent_phone') and extracted['phone']:
                listing['agent_phone'] = extracted['phone']
            if not listing.get('agent_email') and extracted['email']:
                listing['agent_email'] = extracted['email']

        result = {
            **listing,
            '_score': score,
            '_components': scored['components'],
            '_score_weights': config.get('score_weights'),
            '_exclusions': scored['exclusions'],
            '_list_ids': list(list_ids_by_key.get(key, ())),
            '_note': all_notes.get(key, ''),
            '_workflow': workflows_by_key[key],
            '_explanation': explain_property(
                listing,
                scored['score'],
                scored['components'],
                scored['exclusions'],
                purchase_estimate,
            ),
            '_commute': commute_estimate(listing, config.get('commute_destinations', [])),
        }
        if full_read:
            result['_is_duplicate'] = key in duplicate_keys
            result['_purchase_estimate'] = purchase_estimate
        results.append(result)

    if full_read:
        results.sort(key=lambda item: (item['_score'] is None, -(item['_score'] or 0)))
    return results
