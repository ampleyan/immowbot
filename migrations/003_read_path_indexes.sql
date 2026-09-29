CREATE INDEX IF NOT EXISTS listing_versions_listing_observed_at_idx
    ON listing_versions (listing_id, observed_at);

CREATE INDEX IF NOT EXISTS listing_versions_listing_price_id_idx
    ON listing_versions (listing_id, ((payload_json->>'price')::numeric), id);

CREATE INDEX IF NOT EXISTS list_items_listing_idx
    ON list_items (source, source_listing_id, list_id);

CREATE INDEX IF NOT EXISTS alerts_user_id_id_idx
    ON alerts (user_id, id DESC);

DROP INDEX IF EXISTS listings_source_listing_id_idx;
