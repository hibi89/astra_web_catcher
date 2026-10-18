PRAGMA foreign_keys=ON;
CREATE TABLE accounts(
 account_key TEXT PRIMARY KEY, country TEXT NOT NULL CHECK(country IN ('KR','US','JP')),
 collection_status TEXT NOT NULL, posts_available INTEGER NOT NULL,
 followers_at_collection INTEGER, error_code TEXT
);
CREATE TABLE posts(
 post_id TEXT PRIMARY KEY, account_key TEXT NOT NULL REFERENCES accounts(account_key),
 country TEXT NOT NULL, posted_at TEXT NOT NULL, post_date TEXT NOT NULL,
 hour_kst INTEGER NOT NULL CHECK(hour_kst BETWEEN 0 AND 23), media_type TEXT NOT NULL,
 product_type TEXT NOT NULL, likes INTEGER CHECK(likes IS NULL OR likes>=0),
 comments INTEGER CHECK(comments IS NULL OR comments>=0),
 reactions INTEGER CHECK(reactions IS NULL OR reactions>=0),
 followers_at_collection INTEGER, media_rows INTEGER NOT NULL,
 collected_at TEXT NOT NULL
);
CREATE TABLE media(
 media_id TEXT PRIMARY KEY, post_id TEXT NOT NULL REFERENCES posts(post_id),
 media_type TEXT NOT NULL, media_role TEXT
);
CREATE INDEX idx_posts_country_date ON posts(country,post_date);
CREATE INDEX idx_posts_reactions ON posts(country,reactions DESC);
CREATE INDEX idx_media_post ON media(post_id);
