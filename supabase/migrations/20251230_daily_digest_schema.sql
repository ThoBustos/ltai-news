-- Daily Digest Schema Enhancement
-- Adds comprehensive digest fields and references table for cross-day tracking

-- 1. Enhance daily_digests table with new columns
ALTER TABLE daily_digests
ADD COLUMN IF NOT EXISTS content_json JSONB,
ADD COLUMN IF NOT EXISTS formatted_markdown TEXT,
ADD COLUMN IF NOT EXISTS keywords TEXT[],
ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(3, 2),
ADD COLUMN IF NOT EXISTS video_count INTEGER,
ADD COLUMN IF NOT EXISTS channels_included TEXT[];

-- Add GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_daily_digests_content_json
ON daily_digests USING GIN (content_json);

-- Add index for keywords array
CREATE INDEX IF NOT EXISTS idx_daily_digests_keywords
ON daily_digests USING GIN (keywords);

-- 2. Create references table for cross-day tracking
CREATE TABLE IF NOT EXISTS digest_references (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_type TEXT NOT NULL,  -- 'book', 'paper', 'framework', 'concept', 'person', 'community'
    name TEXT NOT NULL,
    author TEXT,
    url TEXT,
    description TEXT,
    first_seen_date DATE NOT NULL,
    mention_count INTEGER DEFAULT 1,
    digest_ids UUID[] DEFAULT '{}',  -- Array of digest IDs where referenced
    video_ids TEXT[] DEFAULT '{}',   -- Array of video IDs where mentioned
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT unique_reference_type_name UNIQUE(reference_type, name)
);

-- Create indexes for references table
CREATE INDEX IF NOT EXISTS idx_references_type ON digest_references(reference_type);
CREATE INDEX IF NOT EXISTS idx_references_name ON digest_references(name);
CREATE INDEX IF NOT EXISTS idx_references_mention_count ON digest_references(mention_count DESC);
CREATE INDEX IF NOT EXISTS idx_references_first_seen ON digest_references(first_seen_date);
CREATE INDEX IF NOT EXISTS idx_references_digest_ids ON digest_references USING GIN(digest_ids);
CREATE INDEX IF NOT EXISTS idx_references_video_ids ON digest_references USING GIN(video_ids);

-- Add trigger for updated_at on references
DROP TRIGGER IF EXISTS update_digest_references_updated_at ON digest_references;
CREATE TRIGGER update_digest_references_updated_at
    BEFORE UPDATE ON digest_references
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 3. Optional: Create subscribers table (if not managed by frontend)
CREATE TABLE IF NOT EXISTS subscribers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    is_active BOOLEAN DEFAULT true,
    preferences JSONB DEFAULT '{}',
    subscribed_at TIMESTAMPTZ DEFAULT now(),
    unsubscribed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email);
CREATE INDEX IF NOT EXISTS idx_subscribers_active ON subscribers(is_active) WHERE is_active = true;

-- Add comments for documentation
COMMENT ON TABLE digest_references IS 'Cross-day reference tracking for books, frameworks, concepts, people, and communities';
COMMENT ON COLUMN digest_references.reference_type IS 'Type: book, paper, framework, concept, person, community';
COMMENT ON COLUMN digest_references.mention_count IS 'Total number of times this reference has been mentioned across all digests';
COMMENT ON COLUMN digest_references.digest_ids IS 'Array of digest UUIDs where this reference appears';
COMMENT ON COLUMN digest_references.video_ids IS 'Array of video IDs where this reference was mentioned';

COMMENT ON COLUMN daily_digests.content_json IS 'Full structured digest content in JSON format';
COMMENT ON COLUMN daily_digests.formatted_markdown IS 'Pre-rendered markdown version for display';
COMMENT ON COLUMN daily_digests.keywords IS 'Array of keywords for search and categorization';
COMMENT ON COLUMN daily_digests.confidence_score IS 'LLM confidence score for the digest (0.0-1.0)';
COMMENT ON COLUMN daily_digests.video_count IS 'Number of videos included in this digest';
COMMENT ON COLUMN daily_digests.channels_included IS 'Array of channel IDs included in this digest';

-- =============================================================================
-- 4. Video Analysis V2 Schema Enhancement
-- Adds deep extraction fields for quotes, frameworks, statistics, and section analysis
-- =============================================================================

-- Add new V2 columns to video_processed_data table
ALTER TABLE video_processed_data
ADD COLUMN IF NOT EXISTS teaser_hooks JSONB,
ADD COLUMN IF NOT EXISTS keywords JSONB,
ADD COLUMN IF NOT EXISTS direct_quotes JSONB,
ADD COLUMN IF NOT EXISTS analogies_metaphors JSONB,
ADD COLUMN IF NOT EXISTS frameworks_shared JSONB,
ADD COLUMN IF NOT EXISTS statistics_data JSONB,
ADD COLUMN IF NOT EXISTS section_analysis JSONB;

-- Add indexes for new JSONB fields (for efficient querying)
CREATE INDEX IF NOT EXISTS idx_video_processed_data_keywords
ON video_processed_data USING GIN(keywords);

CREATE INDEX IF NOT EXISTS idx_video_processed_data_direct_quotes
ON video_processed_data USING GIN(direct_quotes);

CREATE INDEX IF NOT EXISTS idx_video_processed_data_frameworks_shared
ON video_processed_data USING GIN(frameworks_shared);

CREATE INDEX IF NOT EXISTS idx_video_processed_data_statistics_data
ON video_processed_data USING GIN(statistics_data);

-- Add comments for documentation
COMMENT ON COLUMN video_processed_data.teaser_hooks IS 'V2: 3 compelling teaser sentences for engagement';
COMMENT ON COLUMN video_processed_data.keywords IS 'V2: 8-15 keywords for categorization and discoverability';
COMMENT ON COLUMN video_processed_data.direct_quotes IS 'V2: 5-10 verbatim quotes capturing aha moments';
COMMENT ON COLUMN video_processed_data.analogies_metaphors IS 'V2: Analogies and metaphors used to explain concepts';
COMMENT ON COLUMN video_processed_data.frameworks_shared IS 'V2: Mental models and frameworks explained in the video';
COMMENT ON COLUMN video_processed_data.statistics_data IS 'V2: Numbers, statistics, and quantified claims';
COMMENT ON COLUMN video_processed_data.section_analysis IS 'V2: Deep section-by-section analysis with summaries and key points';
