-- Enable Write-Ahead Logging (WAL) mode for better concurrency.
-- WAL mode allows readers to operate concurrently with a single writer,
-- which is ideal for web applications.
-- Reference: https://www.sqlite.org/wal.html
PRAGMA journal_mode = WAL;

-- Create users table with STRICT to enforce type checking.
-- Stores user accounts with username/password authentication.
-- Reference: https://www.sqlite.org/stricttables.html
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
) STRICT;

-- Create feeds table with STRICT to enforce type checking.
-- STRICT prevents type-related data corruption by enforcing that:
-- - volume_ul must be INTEGER (not text or other types)
-- - datetime must be TEXT (not numeric or other types)
-- - user_id must be INTEGER (foreign key to users)
-- Reference: https://www.sqlite.org/stricttables.html
CREATE TABLE feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volume_ul INTEGER NOT NULL,
    datetime TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) STRICT;

CREATE INDEX idx_feeds_datetime ON feeds(datetime DESC);
CREATE INDEX idx_users_username ON users(username);

-- Create sessions table for persistent session storage
-- Sessions don't expire and are stored in the database
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) STRICT;

CREATE INDEX idx_sessions_user_id ON sessions(user_id);

PRAGMA user_version = 1;
