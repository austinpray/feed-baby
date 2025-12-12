-- Enable Write-Ahead Logging (WAL) mode for better concurrency.
-- WAL mode allows readers to operate concurrently with a single writer,
-- which is ideal for web applications.
-- Reference: https://www.sqlite.org/wal.html
PRAGMA journal_mode = WAL;

-- Create feeds table with STRICT to enforce type checking.
-- STRICT prevents type-related data corruption by enforcing that:
-- - volume_ul must be INTEGER (not text or other types)
-- - datetime must be TEXT (not numeric or other types)
-- Reference: https://www.sqlite.org/stricttables.html
CREATE TABLE feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volume_ul INTEGER NOT NULL,
    datetime TEXT NOT NULL
) STRICT;

CREATE INDEX idx_feeds_datetime ON feeds(datetime DESC);

PRAGMA user_version = 1;
