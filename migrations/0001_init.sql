CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volume_ul INTEGER NOT NULL,
    datetime TEXT NOT NULL,
    -- user_id is nullable to allow feeds from before authentication was added
    user_id INTEGER REFERENCES users(id)
);

CREATE INDEX idx_feeds_datetime ON feeds(datetime DESC);
CREATE INDEX idx_users_username ON users(username);

PRAGMA user_version = 1;
