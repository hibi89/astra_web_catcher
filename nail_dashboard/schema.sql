PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS report_runs (
 id INTEGER PRIMARY KEY, label TEXT NOT NULL, period_start TEXT NOT NULL, period_end TEXT NOT NULL,
 created_at TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'seed', CHECK (period_start <= period_end)
);
CREATE TABLE IF NOT EXISTS brands (
 id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL UNIQUE,
 business_type TEXT NOT NULL, follower_count INTEGER NOT NULL CHECK(follower_count >= 0), color TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
 id INTEGER PRIMARY KEY, report_id INTEGER NOT NULL REFERENCES report_runs(id),
 brand_id INTEGER NOT NULL REFERENCES brands(id), posted_at TEXT NOT NULL, hour_kst INTEGER NOT NULL CHECK(hour_kst BETWEEN 0 AND 23),
 medium TEXT NOT NULL CHECK(medium IN ('reel','carousel','image')),
 purpose TEXT NOT NULL, treatment TEXT NOT NULL CHECK(treatment IN ('direct','sheet')),
 likes INTEGER NOT NULL CHECK(likes >= 0), comments INTEGER NOT NULL CHECK(comments >= 0),
 views INTEGER CHECK(views IS NULL OR views >= 0), analyzed INTEGER NOT NULL CHECK(analyzed IN (0,1)),
 url TEXT, UNIQUE(report_id,brand_id,posted_at,hour_kst,medium,purpose,id)
);
CREATE TABLE IF NOT EXISTS tags (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL
 CHECK(category IN ('technique','color','product','season','content')),
 UNIQUE(name, category)
);
CREATE TABLE IF NOT EXISTS post_tags (
 post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
 tag_id INTEGER NOT NULL REFERENCES tags(id), PRIMARY KEY(post_id,tag_id)
);
CREATE INDEX IF NOT EXISTS idx_posts_report_brand ON posts(report_id,brand_id,analyzed,posted_at);
CREATE INDEX IF NOT EXISTS idx_posts_rank ON posts(report_id,brand_id,analyzed,likes,comments);
CREATE INDEX IF NOT EXISTS idx_post_tags_tag ON post_tags(tag_id,post_id);
