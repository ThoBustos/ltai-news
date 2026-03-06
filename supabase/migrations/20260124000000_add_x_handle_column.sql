-- Add x_handle column for X/Twitter handles
-- Separate from YouTube handle field to avoid conflicts
ALTER TABLE channels ADD COLUMN IF NOT EXISTS x_handle TEXT;

-- Add comment for clarity
COMMENT ON COLUMN channels.x_handle IS 'X/Twitter handle (e.g., @LatentSpacePod). Separate from YouTube handle field.';

-- Create index for lookups
CREATE INDEX IF NOT EXISTS idx_channels_x_handle ON channels(x_handle);
