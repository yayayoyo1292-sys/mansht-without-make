
CREATE TABLE IF NOT EXISTS publish_log (
    id          SERIAL PRIMARY KEY,
    article_id  INT     NOT NULL,
    queue_id    INT,
    platform    TEXT    NOT NULL,   
    status      TEXT    NOT NULL,   
    fingerprint TEXT    UNIQUE NOT NULL,
    error_msg   TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_publish_log_article_platform
    ON publish_log (article_id, platform, status);


ALTER TABLE news_queue ADD COLUMN IF NOT EXISTS telegram_attempts   INT DEFAULT 0;
ALTER TABLE news_queue ADD COLUMN IF NOT EXISTS instagram_attempts  INT DEFAULT 0;
ALTER TABLE news_queue ADD COLUMN IF NOT EXISTS twitter_attempts    INT DEFAULT 0;
ALTER TABLE news_queue ADD COLUMN IF NOT EXISTS facebook_attempts   INT DEFAULT 0;
