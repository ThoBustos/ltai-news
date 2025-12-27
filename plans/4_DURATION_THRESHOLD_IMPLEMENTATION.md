# LTAI News - Duration Threshold Implementation Guide

## Overview
This document outlines the implementation of a simplified per-channel video duration threshold system. The new logic enforces a hardcoded 3-minute minimum for all videos while allowing custom thresholds per channel via configuration.

## Current State Analysis

### ✅ What's Currently Implemented
- Global `MIN_VIDEO_DURATION_MINUTES` setting (default: 4, currently: 20)
- `BYPASS_DURATION_CHANNELS` list that completely bypasses duration checks
- Duration filtering logic in `ChannelTracker.fetch_videos_in_window()` and `fetch_recent_videos()`
- Boolean `bypass_duration` flag passed to video fetching methods

### ❌ Problems with Current Implementation
1. **Binary Logic**: The bypass system is all-or-nothing - channels either bypass completely or use global threshold
2. **No Hard Minimum**: Bypassed channels can process videos of any duration (even < 1 minute)
3. **No Per-Channel Thresholds**: Cannot set different thresholds for different channels (e.g., Stripe: 20 mins, Alex Hormozi: 5 mins)
4. **Edge Cases**: Alex Hormozi videos below 3 minutes were processed when they shouldn't have been
5. **Too Many Variables**: Multiple configuration variables (`MIN_VIDEO_DURATION_MINUTES`, `BYPASS_DURATION_CHANNELS`) create confusion

## Requirements

### Core Rules
1. **Hard Minimum**: No video below 3 minutes will be processed, regardless of channel (hardcoded in code)
2. **Default Threshold**: If no custom threshold is specified for a channel, default to 3 minutes (hard minimum)
3. **Per-Channel Override**: Channels can have custom thresholds via `CHANNEL_DURATION_THRESHOLDS` environment variable
4. **Threshold Logic**: `final_threshold = max(3_minutes, channel_threshold_if_exists)`

### Configuration Format
```bash
# Per-channel custom thresholds (format: channel:minutes,channel:minutes)
# Channels not listed here default to 3 minutes (hard minimum)
CHANNEL_DURATION_THRESHOLDS=@stripe:20,@AlexHormozi:5
```

### Example Scenarios
- **Stripe** (custom: 20 mins): Processes videos ≥ 20 minutes
- **Alex Hormozi** (custom: 5 mins): Processes videos ≥ 5 minutes (but still enforces 3-min hard floor)
- **Generic Channel** (no custom): Processes videos ≥ 3 minutes (hardcoded default)
- **Any Channel**: Videos < 3 minutes are always rejected

## Summary: What We'll Have

### Environment Variables (Simplified)
- ✅ `TRACKED_CHANNELS` - List of channels to track
- ✅ `CHANNEL_DURATION_THRESHOLDS` - Custom thresholds per channel (format: `@channel:minutes,@channel:minutes`)
- ❌ **REMOVED**: `MIN_VIDEO_DURATION_MINUTES` - No longer needed (hardcoded to 3 minutes)
- ❌ **REMOVED**: `BYPASS_DURATION_CHANNELS` - No longer needed (use `CHANNEL_DURATION_THRESHOLDS` instead)

### Code Logic (Simplified)
- Hardcoded 3-minute minimum (no env var)
- Pass `Channel` object instead of separate `channel_name` and `channel_handle` parameters
- Single method `get_min_duration_for_channel(channel: Channel)` that returns threshold in seconds
- Clean lookup helper `_get_channel_threshold(channel: Channel)` for threshold resolution

### Complete `.env.example` Configuration

```bash
# Channel Tracking
TRACKED_CHANNELS=@lets-talk-ai,@latentspacepod,@limitless-ft,@Fireship,@stripe,@WeightsBiases,@Deeplearningai,@ycombinator,@mindsetmentorpodcast,@AlexHormozi,@LennysPodcast,@AcquiredFM,@a16z,@twimlai,@aiDotEngineer,@lexfridman,@hubermanlab,@DataIndependent,@daltonplusmichael,@DwarkeshPatel,@pragmaticengineer
CONTENT_LOOKBACK_HOURS=168  # Default lookback for all channels

# Video Duration Configuration
# Hard floor: 3 minutes (enforced in code) - no videos below this will be processed
# Per-channel thresholds (format: channel:minutes,channel:minutes)
# Channels not listed here default to 3 minutes (hard minimum)
CHANNEL_DURATION_THRESHOLDS=@stripe:20,@AlexHormozi:5

# VIP Channel Configuration (for extended lookback - separate from duration)
BYPASS_LOOKBACK_CHANNELS=  # Channels that need deeper historical scan
EXTENDED_LOOKBACK_HOURS=720  # How far back to scan VIP channels (default: 30 days)
```

**Key Points:**
- All 21 channels listed in `TRACKED_CHANNELS`
- Only 2 channels have custom thresholds: `@stripe:20` and `@AlexHormozi:5`
- All other channels default to 3 minutes (hardcoded minimum)
- No `MIN_VIDEO_DURATION_MINUTES` or `BYPASS_DURATION_CHANNELS` variables

## Implementation Plan

### Phase 1: Configuration Layer Updates

#### 1.1 Update Settings Class
**File:** `src/app/config/settings.py`

**Changes:**
1. **REMOVE** `min_video_duration_minutes` field entirely
2. **REMOVE** `bypass_duration_channels_raw` field and `bypass_duration_channels` computed property
3. Add `channel_duration_thresholds_raw` field to store raw environment variable
4. Add `@computed_field` property `channel_duration_thresholds` that parses the string into a `Dict[str, int]`

**New Field:**
```python
channel_duration_thresholds_raw: Optional[str] = Field(
    default=None,
    alias="CHANNEL_DURATION_THRESHOLDS",
    description="Comma-separated list of channel:minutes pairs (e.g., @stripe:20,@AlexHormozi:5)",
    exclude=True,
)
```

**New Computed Property:**
```python
@computed_field
@property
def channel_duration_thresholds(self) -> Dict[str, int]:
    """Parse CHANNEL_DURATION_THRESHOLDS into a dictionary mapping channel names to minutes."""
    if self.channel_duration_thresholds_raw is None or not self.channel_duration_thresholds_raw.strip():
        return {}
    
    thresholds = {}
    for pair in self.channel_duration_thresholds_raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            channel, minutes_str = pair.rsplit(":", 1)
            channel = channel.strip()
            try:
                minutes = int(minutes_str.strip())
                if minutes >= 0:  # Validate non-negative
                    thresholds[channel.lower()] = minutes
            except ValueError:
                logger.warning(f"Invalid threshold value '{minutes_str}' for channel '{channel}', skipping")
    
    return thresholds
```

**Removed Fields:**
- `min_video_duration_minutes` - No longer needed (hardcoded to 3 minutes)
- `bypass_duration_channels_raw` - No longer needed
- `bypass_duration_channels` computed property - No longer needed

### Phase 2: Channel Tracker Service Updates

#### 2.1 Add Threshold Resolution Helper Method
**File:** `src/app/services/channel_tracker.py`

**New Helper Method:**
```python
def _get_channel_threshold(self, channel: Channel) -> Optional[int]:
    """
    Get custom threshold in minutes for channel, or None if not found.
    
    Checks both channel handle and name (case-insensitive).
    
    Args:
        channel: Channel object
    
    Returns:
        Threshold in minutes, or None if not found
    """
    thresholds = self.settings.channel_duration_thresholds
    
    # Check by handle first (more specific), then name
    for identifier in [channel.handle, channel.name]:
        if identifier and identifier.lower() in thresholds:
            return thresholds[identifier.lower()]
    
    return None
```

#### 2.2 Add Main Threshold Resolution Method
**File:** `src/app/services/channel_tracker.py`

**New Method:**
```python
def get_min_duration_for_channel(self, channel: Channel) -> int:
    """
    Get minimum duration threshold for a channel in seconds.
    
    Logic:
    1. Check if channel has custom threshold
    2. If found, use max(3_minutes, custom_threshold)
    3. Otherwise, default to 3 minutes (hard minimum)
    
    Args:
        channel: Channel object
    
    Returns:
        Minimum duration in seconds
    """
    HARD_MIN_SECS = 3 * 60  # Hardcoded absolute minimum
    
    custom_minutes = self._get_channel_threshold(channel)
    if custom_minutes:
        return max(HARD_MIN_SECS, custom_minutes * 60)
    else:
        return HARD_MIN_SECS  # Default: 3 minutes
```

#### 2.3 Update `fetch_videos_in_window` Method
**File:** `src/app/services/channel_tracker.py`
**Location:** Line ~592

**Current Logic:**
```python
bypass_duration: bool = False
min_duration_secs = self.settings.min_video_duration_minutes * 60
if not bypass_duration and duration_secs < min_duration_secs:
    # Skip video
```

**New Logic:**
```python
# Remove bypass_duration parameter entirely
# Pass Channel object instead of separate name/handle
# Replace with:
min_duration_secs = self.get_min_duration_for_channel(channel)
if duration_secs < min_duration_secs:
    logger.info(
        f"Skipping video {video_data['id']} - duration {duration_secs}s "
        f"is less than minimum {min_duration_secs}s for channel {channel.name}"
    )
    continue
```

**Method Signature Change:**
```python
# OLD:
def fetch_videos_in_window(self, channel_id: str, window: TimeWindow, bypass_duration: bool = False) -> List[Video]:

# NEW:
def fetch_videos_in_window(self, channel: Channel, window: TimeWindow) -> List[Video]:
```

#### 2.4 Update `fetch_recent_videos` Method
**File:** `src/app/services/channel_tracker.py`
**Location:** Line ~182

**Current Logic:**
```python
bypass_duration: bool = False
min_duration_secs = self.settings.min_video_duration_minutes * 60
if not bypass_duration and duration_secs < min_duration_secs:
    # Skip video
```

**New Logic:**
```python
# Remove bypass_duration parameter
# Pass Channel object instead of separate name/handle
# Replace with:
min_duration_secs = self.get_min_duration_for_channel(channel)
if duration_secs < min_duration_secs:
    logger.info(
        f"Skipping video {video_data['id']} - duration {duration_secs}s "
        f"is less than minimum {min_duration_secs}s for channel {channel.name}"
    )
    continue
```

**Method Signature Change:**
```python
# OLD:
def fetch_recent_videos(
    self, channel_id: str, hours: Optional[int] = None, bypass_duration: bool = False
) -> List[Video]:

# NEW:
def fetch_recent_videos(
    self, channel: Channel, hours: Optional[int] = None
) -> List[Video]:
```

#### 2.5 Update `sync_channel_for_date` Method
**File:** `src/app/services/channel_tracker.py`
**Location:** Line ~486

**Current Logic:**
```python
bypass_duration = any(
    b.lower() in [channel_name.lower(), channel.name.lower(), channel.handle.lower() if channel.handle else ""] 
    for b in self.settings.bypass_duration_channels
)
videos = self.fetch_videos_in_window(channel.id, window, bypass_duration=bypass_duration)
```

**New Logic:**
```python
# Remove bypass_duration check entirely
# Pass Channel object to fetch_videos_in_window
videos = self.fetch_videos_in_window(channel, window)
```

#### 2.6 Update Other Call Sites
**File:** `src/app/services/channel_tracker.py`

**Search for:** All calls to `fetch_videos_in_window` and `fetch_recent_videos`

**Update:** Ensure all call sites pass `Channel` object instead of separate parameters or `bypass_duration` flag

### Phase 3: Configuration File Updates

#### 3.1 Update `.env.example`
**File:** `.env.example`

**Changes:**
1. **REMOVE** `MIN_VIDEO_DURATION_MINUTES` entirely
2. **REMOVE** `BYPASS_DURATION_CHANNELS` entirely
3. Add `CHANNEL_DURATION_THRESHOLDS` with all channels and their thresholds
4. Update comments to clarify hardcoded 3-minute minimum

**Updated Section:**
```bash
# Channel Tracking
TRACKED_CHANNELS=@lets-talk-ai,@latentspacepod,@limitless-ft,@Fireship,@stripe,@WeightsBiases,@Deeplearningai,@ycombinator,@mindsetmentorpodcast,@AlexHormozi,@LennysPodcast,@AcquiredFM,@a16z,@twimlai,@aiDotEngineer,@lexfridman,@hubermanlab,@DataIndependent,@daltonplusmichael,@DwarkeshPatel,@pragmaticengineer
CONTENT_LOOKBACK_HOURS=168  # Default lookback for all channels

# Video Duration Configuration
# Hard floor: 3 minutes (enforced in code) - no videos below this will be processed
# Per-channel thresholds (format: channel:minutes,channel:minutes)
# Channels not listed here default to 3 minutes (hard minimum)
CHANNEL_DURATION_THRESHOLDS=@stripe:20,@AlexHormozi:5

# VIP Channel Configuration (for extended lookback - separate from duration)
BYPASS_LOOKBACK_CHANNELS=  # Channels that need deeper historical scan
EXTENDED_LOOKBACK_HOURS=720  # How far back to scan VIP channels (default: 30 days)
```

**Note:** All channels from `TRACKED_CHANNELS` are listed above. Channels without custom thresholds in `CHANNEL_DURATION_THRESHOLDS` will default to 3 minutes.

### Phase 4: Cleanup (Remove Old Code)

#### 4.1 Remove Deprecated Code
**File:** `src/app/config/settings.py`

**Remove:**
- `min_video_duration_minutes` field
- `bypass_duration_channels_raw` field
- `bypass_duration_channels` computed property

**File:** `src/app/services/channel_tracker.py`

**Remove:**
- All references to `bypass_duration` parameter
- All logic checking `self.settings.bypass_duration_channels`
- All logic using `self.settings.min_video_duration_minutes`

**Note:** No backward compatibility needed - we're removing the old system entirely and using the simplified approach.

## Implementation Checklist

### Configuration Layer
- [ ] **REMOVE** `min_video_duration_minutes` field from `Settings` class
- [ ] **REMOVE** `bypass_duration_channels_raw` field from `Settings` class
- [ ] **REMOVE** `bypass_duration_channels` computed property from `Settings` class
- [ ] Add `channel_duration_thresholds_raw` field to `Settings` class
- [ ] Add `channel_duration_thresholds` computed property with parsing logic
- [ ] Add logging for invalid threshold values during parsing

### Service Layer
- [ ] Add `_get_channel_threshold()` helper method to `ChannelTracker`
- [ ] Add `get_min_duration_for_channel()` method to `ChannelTracker` (takes `Channel` object)
- [ ] Update `fetch_videos_in_window()` signature to take `Channel` object instead of `bypass_duration`
- [ ] Update `fetch_recent_videos()` signature to take `Channel` object instead of `bypass_duration`
- [ ] Update `sync_channel_for_date()` to remove bypass logic and pass `Channel` object
- [ ] Find and update all call sites of video fetching methods to pass `Channel` object
- [ ] Remove all references to `bypass_duration` parameter
- [ ] Remove all references to `self.settings.bypass_duration_channels`
- [ ] Remove all references to `self.settings.min_video_duration_minutes`
- [ ] Add comprehensive logging for threshold decisions

### Configuration Files
- [ ] **REMOVE** `MIN_VIDEO_DURATION_MINUTES` from `.env.example`
- [ ] **REMOVE** `BYPASS_DURATION_CHANNELS` from `.env.example`
- [ ] Add `CHANNEL_DURATION_THRESHOLDS` to `.env.example` with all channels
- [ ] Update comments to clarify hardcoded 3-minute minimum

### Testing & Validation
- [ ] Test with channel that has custom threshold (e.g., @stripe:20)
- [ ] Test with channel that has no custom threshold (should default to 3 minutes)
- [ ] Test with video < 3 minutes (should be rejected for all channels)
- [ ] Test with video between 3-5 minutes for @AlexHormozi (should pass)
- [ ] Test with video between 3-5 minutes for @stripe (should be rejected)
- [ ] Test with video exactly 3 minutes (should pass for all channels)
- [ ] Verify logging output shows correct threshold decisions

## Key Design Decisions

### 1. Hardcoded 3-Minute Floor
**Decision:** Hardcode 3-minute minimum in code, remove `MIN_VIDEO_DURATION_MINUTES` env var
**Rationale:** 
- Simplifies configuration (one less variable)
- Single source of truth (hardcoded constant)
- Prevents edge cases and ensures no videos below 3 minutes are processed

### 2. Pass Channel Object Instead of Separate Parameters
**Decision:** Pass `Channel` object to methods instead of `channel_name` and `channel_handle` separately
**Rationale:** 
- Reduces parameter count
- Cleaner method signatures
- Easier to extend in the future

### 3. Environment Variable Format
**Decision:** Use simple `channel:minutes` format instead of JSON
**Rationale:** 
- Easier to edit in `.env` files
- No need for JSON parsing
- Simple and readable

### 4. Case-Insensitive Matching
**Decision:** Convert channel names/handles to lowercase for matching
**Rationale:** Prevents issues with inconsistent casing in configuration vs. YouTube API responses

### 5. No Backward Compatibility
**Decision:** Remove old system entirely, no migration support
**Rationale:** 
- Cleaner implementation
- Forces proper migration to new system
- Reduces code complexity

## Migration Path

### Step 1: Update Configuration
1. Remove `MIN_VIDEO_DURATION_MINUTES` from `.env` files
2. Remove `BYPASS_DURATION_CHANNELS` from `.env` files
3. Add `CHANNEL_DURATION_THRESHOLDS` with appropriate thresholds:
   - Channels that were bypassed: Add with `:3` (or appropriate threshold)
   - Channels that need custom thresholds: Add with their threshold (e.g., `@stripe:20`)
   - Other channels: No entry needed (will default to 3 minutes)

### Step 2: Code Implementation
1. Remove old fields from `Settings` class
2. Add new `channel_duration_thresholds` parsing
3. Update `ChannelTracker` methods to use new logic
4. Remove all references to old bypass system

### Step 3: Testing
1. Test with channels that have custom thresholds
2. Test with channels that don't have custom thresholds (should default to 3 minutes)
3. Verify hard 3-minute floor is enforced for all channels

## Success Criteria

1. ✅ No videos below 3 minutes are processed for any channel (hardcoded floor)
2. ✅ Channels with custom thresholds use their specified threshold (enforcing 3-min floor)
3. ✅ Channels without custom thresholds default to 3 minutes (hard minimum)
4. ✅ Configuration is simple: only `CHANNEL_DURATION_THRESHOLDS` needed
5. ✅ Logging clearly shows which threshold is being used for each channel
6. ✅ No old bypass system code remains
7. ✅ Clean method signatures using `Channel` objects

## Files to Modify

1. `src/app/config/settings.py` - Remove old fields, add threshold parsing logic
2. `src/app/services/channel_tracker.py` - Update duration filtering logic, remove bypass system
3. `.env.example` - Remove old variables, add `CHANNEL_DURATION_THRESHOLDS` with all channels

## Estimated Implementation Time

- **Configuration Layer**: 20 minutes (removing old code + adding new)
- **Service Layer Updates**: 1-1.5 hours (simplified approach)
- **Testing & Validation**: 1 hour
- **Total**: 2-2.5 hours

## Complete Channel List

All channels currently tracked (from `TRACKED_CHANNELS` and `BYPASS_DURATION_CHANNELS`):
- @lets-talk-ai
- @latentspacepod
- @limitless-ft
- @Fireship
- @stripe
- @WeightsBiases
- @Deeplearningai
- @ycombinator
- @mindsetmentorpodcast
- @AlexHormozi
- @LennysPodcast
- @AcquiredFM
- @a16z
- @twimlai
- @aiDotEngineer
- @lexfridman
- @hubermanlab
- @DataIndependent
- @daltonplusmichael
- @DwarkeshPatel
- @pragmaticengineer

**Example `CHANNEL_DURATION_THRESHOLDS` configuration:**
```bash
CHANNEL_DURATION_THRESHOLDS=@stripe:20,@AlexHormozi:5
```

All other channels will default to 3 minutes (hard minimum).

