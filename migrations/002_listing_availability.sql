ALTER TABLE listings
    ADD COLUMN availability_status TEXT NOT NULL DEFAULT 'active'
        CHECK (availability_status IN ('active', 'gone')),
    ADD COLUMN availability_checked_at TIMESTAMPTZ;
