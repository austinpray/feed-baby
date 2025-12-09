-- Initial database schema
CREATE TABLE feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volume_ul INTEGER NOT NULL,
    datetime TEXT NOT NULL
);

PRAGMA user_version = 1;
