-- Video Analysis Schema Enhancement
-- Adds comprehensive video analysis fields to support LangGraph + Gemini 3.0 Flash workflow

-- Enhance video_processed_data table with video analysis fields
ALTER TABLE video_processed_data 
ADD COLUMN IF NOT EXISTS tldr TEXT,
ADD COLUMN IF NOT EXISTS core_topics JSONB,
ADD COLUMN IF NOT EXISTS lessons_learned JSONB,
ADD COLUMN IF NOT EXISTS detailed_insights TEXT,
ADD COLUMN IF NOT EXISTS sources_referenced JSONB,
ADD COLUMN IF NOT EXISTS concepts_mentioned JSONB,
ADD COLUMN IF NOT EXISTS people_mentioned JSONB,
ADD COLUMN IF NOT EXISTS communities_mentioned JSONB,
ADD COLUMN IF NOT EXISTS metadata_extracted JSONB,
ADD COLUMN IF NOT EXISTS input_tokens INTEGER,
ADD COLUMN IF NOT EXISTS output_tokens INTEGER,
ADD COLUMN IF NOT EXISTS total_tokens INTEGER,
ADD COLUMN IF NOT EXISTS total_cost DECIMAL(10, 6),
ADD COLUMN IF NOT EXISTS total_processing_time_seconds DECIMAL(10, 3),
ADD COLUMN IF NOT EXISTS processing_metadata JSONB;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_video_processed_data_total_cost ON video_processed_data(total_cost);
CREATE INDEX IF NOT EXISTS idx_video_processed_data_processed_at ON video_processed_data(processed_at);
CREATE INDEX IF NOT EXISTS idx_video_processed_data_model_name ON video_processed_data(model_name);

-- Add GIN indexes for JSONB fields (for efficient querying)
CREATE INDEX IF NOT EXISTS idx_video_processed_data_core_topics ON video_processed_data USING GIN(core_topics);
CREATE INDEX IF NOT EXISTS idx_video_processed_data_lessons_learned ON video_processed_data USING GIN(lessons_learned);
CREATE INDEX IF NOT EXISTS idx_video_processed_data_sources_referenced ON video_processed_data USING GIN(sources_referenced);
CREATE INDEX IF NOT EXISTS idx_video_processed_data_concepts_mentioned ON video_processed_data USING GIN(concepts_mentioned);

-- Add comments for documentation
COMMENT ON COLUMN video_processed_data.tldr IS 'AI-generated TLDR summary of the video content';
COMMENT ON COLUMN video_processed_data.core_topics IS 'Array of core topics with categories and importance levels';
COMMENT ON COLUMN video_processed_data.lessons_learned IS 'Categorized lessons (technical/business/general)';
COMMENT ON COLUMN video_processed_data.detailed_insights IS 'Extended analysis and implications';
COMMENT ON COLUMN video_processed_data.sources_referenced IS 'External sources mentioned (papers, books, links, etc.)';
COMMENT ON COLUMN video_processed_data.concepts_mentioned IS 'Key concepts and frameworks discussed';
COMMENT ON COLUMN video_processed_data.people_mentioned IS 'People referenced in the video';
COMMENT ON COLUMN video_processed_data.communities_mentioned IS 'Communities, events, organizations mentioned';
COMMENT ON COLUMN video_processed_data.metadata_extracted IS 'Full video/channel metadata for context';
COMMENT ON COLUMN video_processed_data.input_tokens IS 'Number of input tokens used in analysis';
COMMENT ON COLUMN video_processed_data.output_tokens IS 'Number of output tokens generated';
COMMENT ON COLUMN video_processed_data.total_tokens IS 'Total tokens (input + output)';
COMMENT ON COLUMN video_processed_data.total_cost IS 'Estimated cost in USD for the analysis';
COMMENT ON COLUMN video_processed_data.total_processing_time_seconds IS 'Time taken to complete analysis';
COMMENT ON COLUMN video_processed_data.processing_metadata IS 'Detailed processing info for case studies and debugging';

-- Update the trigger for the enhanced table
DROP TRIGGER IF EXISTS update_video_processed_data_updated_at ON video_processed_data;
CREATE TRIGGER update_video_processed_data_updated_at 
    BEFORE UPDATE ON video_processed_data 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();