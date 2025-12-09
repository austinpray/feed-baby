CREATE TABLE feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volume_ul INTEGER NOT NULL,
    datetime TEXT NOT NULL
);

CREATE INDEX idx_feeds_datetime ON feeds(datetime DESC);

PRAGMA user_version = 1;
