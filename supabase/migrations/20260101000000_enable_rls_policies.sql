-- =============================================================================
-- Row Level Security (RLS) Policies
-- =============================================================================
-- Security Model:
--   - daily_digests: Public read-only (for frontend display)
--   - All other tables: No public access (service_role only)
--
-- IMPORTANT: The anon key is PUBLIC and visible in browser DevTools.
-- RLS is the security boundary, not the key itself.
-- =============================================================================

-- =============================================================================
-- 1. DAILY_DIGESTS - Public read-only
-- =============================================================================
ALTER TABLE daily_digests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "daily_digests_public_read" ON daily_digests
    FOR SELECT
    USING (true);

CREATE POLICY "daily_digests_service_all" ON daily_digests
    FOR ALL
    USING (auth.role() = 'service_role');

-- =============================================================================
-- 2. ALL OTHER TABLES - No public access (service_role only)
-- =============================================================================

-- Channels
ALTER TABLE channels ENABLE ROW LEVEL SECURITY;
CREATE POLICY "channels_service_only" ON channels
    FOR ALL USING (auth.role() = 'service_role');

-- Videos
ALTER TABLE videos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "videos_service_only" ON videos
    FOR ALL USING (auth.role() = 'service_role');

-- Video Transcripts
ALTER TABLE video_transcripts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "video_transcripts_service_only" ON video_transcripts
    FOR ALL USING (auth.role() = 'service_role');

-- Video Processed Data
ALTER TABLE video_processed_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "video_processed_data_service_only" ON video_processed_data
    FOR ALL USING (auth.role() = 'service_role');

-- Digest References
ALTER TABLE digest_references ENABLE ROW LEVEL SECURITY;
CREATE POLICY "digest_references_service_only" ON digest_references
    FOR ALL USING (auth.role() = 'service_role');

-- Subscribers
ALTER TABLE subscribers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "subscribers_service_only" ON subscribers
    FOR ALL USING (auth.role() = 'service_role');

-- =============================================================================
-- VERIFICATION QUERIES (run after migration to confirm)
-- =============================================================================
-- Check RLS is enabled:
--   SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
--
-- Check policies exist:
--   SELECT tablename, policyname, cmd FROM pg_policies WHERE schemaname = 'public';

