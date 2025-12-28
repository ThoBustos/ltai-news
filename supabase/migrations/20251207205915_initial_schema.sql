-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Channels table
CREATE TABLE IF NOT EXISTS channels (
    id TEXT PRIMARY KEY,  -- YouTube channel ID (UC...)
    name TEXT NOT NULL,
    handle TEXT,
    custom_url TEXT,
    description TEXT,
    thumbnail_url TEXT,
    published_at TIMESTAMPTZ,
    subscriber_count INTEGER,
    video_count INTEGER,
    view_count INTEGER,
    uploads_playlist_id TEXT,
    last_synced_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    raw_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT channels_id_unique UNIQUE (id)
);

CREATE INDEX IF NOT EXISTS idx_channels_is_active ON channels(is_active);
CREATE INDEX IF NOT EXISTS idx_channels_last_synced ON channels(last_synced_at);

-- 2. Videos table
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,  -- YouTube video ID
    channel_id TEXT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    duration TEXT,  -- ISO 8601 duration
    duration_seconds INTEGER,
    thumbnail_url TEXT,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'collected', -- collected, processing, processed, failed, skipped
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    processing_error TEXT,
    transcript_fetched BOOLEAN DEFAULT FALSE,
    transcript_error TEXT,
    summary_generated BOOLEAN DEFAULT FALSE,
    tags_extracted BOOLEAN DEFAULT FALSE,
    raw_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT videos_id_unique UNIQUE (id),
    CONSTRAINT videos_status_check CHECK (status IN ('collected', 'processing', 'processed', 'failed', 'skipped'))
);

CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at DESC);

-- 3. Video Transcripts (Separate table for performance)
CREATE TABLE IF NOT EXISTS video_transcripts (
    video_id TEXT PRIMARY KEY REFERENCES videos(id) ON DELETE CASCADE,
    transcript TEXT NOT NULL,
    language_code TEXT DEFAULT 'en',
    extracted_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Video Processed Data (Deep analysis per video)
CREATE TABLE IF NOT EXISTS video_processed_data (
    video_id TEXT PRIMARY KEY REFERENCES videos(id) ON DELETE CASCADE,
    summary TEXT,
    analysis TEXT, -- Core column for extensive analysis
    key_points JSONB, -- Array of strings
    tags JSONB, -- Specific extracted tags
    
    -- Metadata
    model_name TEXT,
    tokens_used INTEGER,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Daily Digests (The final newsletter output)
CREATE TABLE IF NOT EXISTS daily_digests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    publish_date DATE UNIQUE NOT NULL, -- Ensures one digest per day
    title TEXT NOT NULL,
    description TEXT,
    formatted_html TEXT, -- Final email content
    
    -- Source Tracking
    source_video_ids TEXT[], -- Array of YouTube IDs
    source_tweet_ids TEXT[], -- Array of X/Twitter IDs
    
    -- Execution & AI Metadata
    total_tokens_input INTEGER,
    total_tokens_output INTEGER,
    cost_estimate DECIMAL(10, 6),
    agent_metadata JSONB, -- Prompts, logic versions, etc.
    eval_score DECIMAL(3, 2), -- Automated eval score (0.0-1.0)
    
    -- Status
    is_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ,
    recipient_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers
CREATE TRIGGER update_channels_updated_at BEFORE UPDATE ON channels FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_videos_updated_at BEFORE UPDATE ON videos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_daily_digests_updated_at BEFORE UPDATE ON daily_digests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
