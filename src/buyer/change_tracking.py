PHOTO_KEYS = ("images", "image_url_1", "image_url_2")
TRACKED_FIELDS = ("price", "epc_score", "surface_area", "bedrooms", "construction_year", "outdoor_terrace", "outdoor_garden", "description")


def _photos(payload):
    values = []
    if isinstance(payload.get("images"), list):
        values.extend(payload["images"])
    values.extend(payload.get(key) for key in ("image_url_1", "image_url_2"))
    return {str(value) for value in values if value}


def diff_versions(old, new):
    if not old:
        return []
    changes = []
    for field in TRACKED_FIELDS:
        before, after = old.get(field), new.get(field)
        if before != after:
            change_type = "price_reduction" if field == "price" and before and after and after < before else "changed"
            changes.append({"field": field, "old_value": before, "new_value": after, "change_type": change_type})
    before_photos, after_photos = _photos(old), _photos(new)
    added, removed = after_photos - before_photos, before_photos - after_photos
    if added or removed:
        changes.append({"field": "photos", "old_value": len(before_photos), "new_value": len(after_photos), "change_type": "photos_added" if added else "photos_removed", "added": sorted(added), "removed": sorted(removed)})
    return changes
