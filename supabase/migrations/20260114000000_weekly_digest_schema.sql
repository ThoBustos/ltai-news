-- Weekly digest schema for aggregated weekly newsletters
-- Migration: 20260114000000_weekly_digest_schema.sql

-- Weekly digests table
CREATE TABLE IF NOT EXISTS weekly_digests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,

    -- Rendered content
    formatted_html TEXT,
    formatted_markdown TEXT,
    content_json JSONB,

    -- Source tracking
    source_daily_digest_ids UUID[] DEFAULT '{}',
    days_with_content INTEGER DEFAULT 0,

    -- Stats
    total_videos INTEGER DEFAULT 0,
    channels_included TEXT[] DEFAULT '{}',
    keywords TEXT[] DEFAULT '{}',
    confidence_score DECIMAL(3,2),

    -- AI metadata
    total_tokens_input INTEGER,
    total_tokens_output INTEGER,
    cost_estimate DECIMAL(10,6),
    agent_metadata JSONB,

    -- Status
    is_sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ,
    recipient_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_week_start UNIQUE (week_start_date),
    CONSTRAINT valid_week_range CHECK (week_end_date = week_start_date + INTERVAL '6 days')
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_weekly_digests_week_start ON weekly_digests(week_start_date DESC);
CREATE INDEX IF NOT EXISTS idx_weekly_digests_is_sent ON weekly_digests(is_sent);

-- Trigger for updated_at (uses existing function from initial schema)
DROP TRIGGER IF EXISTS update_weekly_digests_updated_at ON weekly_digests;
CREATE TRIGGER update_weekly_digests_updated_at
    BEFORE UPDATE ON weekly_digests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS policies (matching daily_digests pattern)
ALTER TABLE weekly_digests ENABLE ROW LEVEL SECURITY;

-- Public read access (anyone can SELECT, including anon key)
CREATE POLICY "weekly_digests_public_read" ON weekly_digests
    FOR SELECT
    USING (true);

-- Service role full access (INSERT/UPDATE/DELETE)
CREATE POLICY "weekly_digests_service_all" ON weekly_digests
    FOR ALL
    USING (auth.role() = 'service_role');

COMMENT ON TABLE weekly_digests IS 'Weekly aggregated digests summarizing daily content';
COMMENT ON COLUMN weekly_digests.week_start_date IS 'Monday of the week (ISO week start)';
COMMENT ON COLUMN weekly_digests.week_end_date IS 'Sunday of the week';
COMMENT ON COLUMN weekly_digests.source_daily_digest_ids IS 'UUIDs of daily digests included in this weekly';
COMMENT ON COLUMN weekly_digests.days_with_content IS 'Number of days that had content (0-7)';
