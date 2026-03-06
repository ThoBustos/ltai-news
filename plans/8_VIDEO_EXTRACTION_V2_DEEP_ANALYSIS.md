# 8. Video Extraction V2 - Deep Analysis Enhancement

## Overview

This plan enhances the video analysis extraction system to capture maximum value and signal from video content. The update transforms our extraction from a basic summary system to a **dense, compressible intelligence layer** that captures quotes, frameworks, statistics, analogies, and section-by-section analysis.

**Version**: 2.0  
**Prompt Version**: Upgrade from 1.1 → 1.2
**Breaking Changes**: Yes (new fields, schema updates)

---

## Goals

1. **Extract Direct Quotes**: Capture aha moments, bold claims, and memorable phrases verbatim
2. **Capture Analogies & Metaphors**: Identify compression tools speakers use to explain concepts
3. **Extract Frameworks**: Mental models, decision frameworks, and structured thinking approaches
4. **Quantify Everything**: Numbers, statistics, percentages, timelines, and data points
5. **Deep Section Analysis**: Dense paragraph summaries per video section with specifics
6. **Teaser Hooks**: 3 compelling sentences to drive engagement
7. **Keywords**: 8-15 tags for categorization and discoverability
8. **Remove Truncation**: Process full transcripts without the 12K character limit
9. **Compress/Decompress Ready**: Structure data for downstream processing (digest generation)

---

## Current State Analysis

### What We Have (V1.1)

| Field | Type | Quality |
|-------|------|---------|
| `tldr` | TEXT | ✅ Good - 2 paragraphs |
| `key_audience` | TEXT | ✅ Good - 1 sentence |
| `core_topics` | JSONB | ✅ Good - 3-7 topics with category/importance |
| `lessons_learned` | JSONB | ✅ Good - categorized (technical/business/general) |
| `sources_referenced` | JSONB | ⚠️ Shallow - only explicit links |
| `concepts_mentioned` | JSONB | ✅ Good - with descriptions |
| `people_mentioned` | JSONB | ✅ Good - with roles/affiliations |
| `communities_mentioned` | JSONB | ✅ Good |
| `detailed_insights` | TEXT | ✅ Good - synthesis |

### What's Missing (Gap Analysis)

| Missing Element | Impact |
|-----------------|--------|
| **Direct Quotes** | No memorable phrases for digests/social |
| **Analogies/Metaphors** | Missing compression tools that make ideas stick |
| **Frameworks** | Mental models not captured as reusable structures |
| **Statistics/Numbers** | Concrete data points not extracted |
| **Section Analysis** | No granular breakdown of video segments |
| **Teaser Hooks** | No click-worthy sentences for engagement |
| **Keywords** | No tags for categorization/search |

### Current Truncation Issue

```python
# src/app/agents/video_analyzer/nodes.py, line 103
"transcript": transcript["text"][:12000]  # PROBLEM: Truncates at 12K chars
```

**Impact**: For a 12:30 video with ~27K char transcript, we're only processing ~44% of the content. Key insights from the second half are lost.

---

## Architecture Changes

### File Structure (No New Files, Only Updates)

```
src/app/
├── models/
│   └── video_analysis.py          # UPDATE: Add new Pydantic models
├── agents/
│   └── video_analyzer/
│       ├── prompts.py             # UPDATE: V2 prompt with new extractions
│       ├── nodes.py               # UPDATE: Remove truncation, map new fields
│       └── workflow.py            # UPDATE: Map new response fields
├── repositories/
│   └── video_analysis_repository.py  # UPDATE: Save new fields
└── supabase/
    └── migrations/
        └── 20250101_video_analysis_v2.sql  # NEW: Add columns
```

---

## Phase 1: Data Models Update

### File: `src/app/models/video_analysis.py`

#### 1.1 Add New Extraction Models

**Location**: Add after existing models (around line 38)

```python
# === NEW V2 EXTRACTION MODELS ===

class DirectQuote(BaseModel):
    """A direct quote capturing a key insight or aha moment."""
    quote: str = Field(description="Exact quote from the transcript - verbatim")
    speaker: Optional[str] = Field(None, description="Speaker if identifiable from context")
    context: str = Field(description="What topic/point this quote addresses")
    impact: Literal["insight", "prediction", "contrarian", "actionable", "synthesis"] = Field(
        description="Why this quote matters - the type of value it delivers"
    )


class AnalogyMetaphor(BaseModel):
    """An analogy or metaphor used to explain a concept."""
    analogy: str = Field(description="The analogy or metaphor as stated")
    explains: str = Field(description="What concept or idea it illuminates")
    effectiveness: Literal["high", "medium"] = Field(
        description="How well it conveys the idea - high if memorable and clear"
    )


class FrameworkMentioned(BaseModel):
    """A framework, mental model, or structured thinking approach shared."""
    name: str = Field(description="Framework or mental model name")
    description: str = Field(description="How it works or is applied - actionable explanation")
    application: str = Field(description="Specific use case or context from the video")
    source: Optional[str] = Field(None, description="Origin if mentioned (book, person, company)")


class StatisticDataPoint(BaseModel):
    """A concrete number, statistic, or quantified claim."""
    value: str = Field(description="The exact number, percentage, or statistic")
    context: str = Field(description="What it measures or represents")
    significance: str = Field(description="Why this number matters - the implication")


class VideoSection(BaseModel):
    """Deep analysis of a video section/segment."""
    title: str = Field(description="Section title or theme - descriptive")
    timestamp_range: Optional[str] = Field(None, description="Approximate time range if determinable")
    summary: str = Field(description="Dense 2-3 sentence summary with specifics - no generic statements")
    key_points: List[str] = Field(description="3-5 bullet points capturing core value")
    frameworks_used: List[str] = Field(default_factory=list, description="Frameworks referenced in this section")
    notable_quotes: List[str] = Field(default_factory=list, description="Best 1-2 quotes from this section")
```

#### 1.2 Update VideoAnalysisResponse Model

**Location**: Replace the existing `VideoAnalysisResponse` class (around line 40-60)

```python
class VideoAnalysisResponse(BaseModel):
    """Master structured response for comprehensive video analysis - V2.0."""
    
    # === CORE SUMMARY ===
    tldr: str = Field(description="2-3 paragraph dense summary with key numbers, frameworks, and insights")
    key_audience: str = Field(description="Who benefits most from this content and why specifically")
    teaser_hooks: List[str] = Field(description="Exactly 3 compelling sentences to tease the content")
    keywords: List[str] = Field(description="8-15 keywords for discoverability and categorization")
    
    # === STRUCTURED EXTRACTIONS ===
    core_topics: List[CoreTopic] = Field(description="3-7 main topics identified")
    lessons_learned: Dict[str, List[str]] = Field(
        description="Lessons by category (technical/business/general)"
    )
    sources_referenced: List[SourceReference] = Field(description="External sources mentioned")
    concepts_mentioned: List[ConceptMention] = Field(description="Key concepts and frameworks")
    people_mentioned: List[PersonMention] = Field(description="People referenced")
    communities_mentioned: List[CommunityMention] = Field(description="Communities, events, organizations")
    
    # === NEW V2: DEPTH EXTRACTIONS ===
    direct_quotes: List[DirectQuote] = Field(
        description="5-10 most impactful quotes - verbatim aha moments"
    )
    analogies_metaphors: List[AnalogyMetaphor] = Field(
        description="Analogies and metaphors used to explain concepts"
    )
    frameworks_shared: List[FrameworkMentioned] = Field(
        description="Mental models and frameworks explained"
    )
    statistics_data: List[StatisticDataPoint] = Field(
        description="Numbers, stats, and quantified claims"
    )
    
    # === SECTION-BY-SECTION ANALYSIS ===
    section_analysis: List[VideoSection] = Field(
        description="Deep analysis of each major section/segment"
    )
    
    # === SYNTHESIS ===
    detailed_insights: str = Field(description="Extended analysis connecting all elements")
    
    # === CONFIDENCE ===
    confidence_scores: Dict[str, float] = Field(
        description="Confidence per extraction category (0.0-1.0)"
    )
```

#### 1.3 Update VideoAnalysisComplete Model

**Location**: Update the existing `VideoAnalysisComplete` class (around line 63-99)

```python
class VideoAnalysisComplete(BaseModel):
    """Complete video analysis result for database storage - V2.0."""
    
    video_id: str
    
    # === CORE ===
    tldr: str
    key_audience: str
    teaser_hooks: List[str] = Field(default_factory=list)  # NEW
    keywords: List[str] = Field(default_factory=list)  # NEW
    
    # === STRUCTURED ===
    core_topics: List[Dict[str, Any]]
    lessons_learned: Dict[str, List[str]]
    detailed_insights: str
    sources_referenced: List[Dict[str, Any]]
    concepts_mentioned: List[Dict[str, Any]]
    people_mentioned: List[Dict[str, Any]]
    communities_mentioned: List[Dict[str, Any]]
    
    # === NEW V2: DEPTH EXTRACTIONS ===
    direct_quotes: List[Dict[str, Any]] = Field(default_factory=list)
    analogies_metaphors: List[Dict[str, Any]] = Field(default_factory=list)
    frameworks_shared: List[Dict[str, Any]] = Field(default_factory=list)
    statistics_data: List[Dict[str, Any]] = Field(default_factory=list)
    section_analysis: List[Dict[str, Any]] = Field(default_factory=list)
    
    # === METADATA ===
    metadata_extracted: Dict[str, Any]
    
    # === PROCESSING ===
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost: Optional[float] = None
    total_processing_time_seconds: float
    confidence_scores: Dict[str, float]
    processing_metadata: Optional[Dict[str, Any]] = None
    
    # === MODEL INFO ===
    model_name: str = "gemini-3-flash-preview"
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
```

---

## Phase 2: Prompt Update

### File: `src/app/agents/video_analyzer/prompts.py`

**Action**: Replace the entire file with V2 prompt

```python
"""Prompt management for video analysis using Opik ChatPrompt - V2.0."""

from typing import Any, Dict, List
import opik


class VideoAnalysisPrompts:
    """Centralized prompt management using Opik ChatPrompt system."""

    CURRENT_VERSION = "2.0"

    @staticmethod
    def get_master_extraction_prompt() -> opik.ChatPrompt:
        """Get comprehensive analysis prompt with structured output schema - V2.0."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": """You are an expert analyst extracting maximum value from technical video content.

Your mission: Transform video transcripts into dense, actionable intelligence that captures every piece of signal.

EXTRACTION PRINCIPLES:
- Capture EXACT quotes that deliver aha moments - the phrases viewers will remember and share
- Extract CONCRETE numbers, statistics, and quantified claims - specificity is signal
- Identify FRAMEWORKS and mental models that can be applied elsewhere
- Find ANALOGIES that make complex ideas stick
- Analyze EACH SECTION deeply with specifics - don't summarize generically, synthesize with detail
- Surface CONTRARIAN views and non-obvious insights
- Make everything COMPRESSIBLE: structured for downstream processing and digest generation

You must respond with valid JSON only. No text before or after the JSON."""
            },
            {
                "role": "user",
                "content": """VIDEO TITLE: {{title}}
VIDEO DESCRIPTION: {{description}}
CHANNEL: {{channel_name}}
VIDEO URL: {{url}}
PUBLISHED AT: {{published_at}}

FULL TRANSCRIPT:
{{transcript}}

---

EXTRACT THE FOLLOWING WITH MAXIMUM DEPTH AND PRECISION:

## 1. TLDR (2-3 paragraphs)
Write a DENSE summary that includes:
- Core thesis and why it matters NOW
- Key numbers/statistics mentioned
- Frameworks or mental models introduced
- Who should care and what they should do differently

## 2. KEY AUDIENCE
Who specifically benefits from this content and WHY - be precise about the value they'll get.

## 3. TEASER HOOKS (exactly 3)
Three compelling single sentences that would make someone click/watch/read more.
Focus on: surprising claims, concrete benefits, contrarian takes, specific numbers.
These should work as social media posts or newsletter teasers.

## 4. KEYWORDS (8-15)
Tags for categorization: themes, technologies, concepts, industries, people, methodologies.
Mix of broad and specific terms for discoverability.

## 5. CORE TOPICS (3-7)
Main subjects with category (technical/business/philosophy/general) and importance (high/medium/low).

## 6. LESSONS LEARNED
Actionable takeaways organized by:
- Technical: implementation insights, architecture decisions, tooling choices, code patterns
- Business: strategy, operations, market dynamics, competitive positioning
- General: career advice, mindset shifts, industry trends, meta-observations

## 7. DIRECT QUOTES (5-10)
The most impactful VERBATIM quotes from the transcript. Prioritize:
- Aha moments that crystallize insights in memorable ways
- Bold predictions or contrarian claims that challenge conventional thinking
- Memorable phrasings that stick - quotable one-liners
- Actionable advice stated clearly
- Synthesis statements that connect multiple ideas
Include speaker attribution (if identifiable) and context for each.

## 8. ANALOGIES & METAPHORS
Every analogy or metaphor used to explain concepts.
These are compression tools - capture them precisely as they help ideas stick.
Rate effectiveness as high (memorable, clear) or medium.

## 9. FRAMEWORKS SHARED
Mental models, decision frameworks, or structured thinking approaches explained.
Include: 
- Name (official or descriptive)
- How it works (actionable description)
- Application context from the video
- Source if mentioned (book, person, company)

## 10. STATISTICS & DATA POINTS
Every concrete number, percentage, timeline, or quantified claim.
Include:
- The exact value as stated
- What it measures/represents
- Why it's significant (the implication)

## 11. SECTION-BY-SECTION ANALYSIS
Break the video into logical sections (3-7 sections typically). For each:
- Title: Descriptive theme name
- Timestamp range: Approximate if determinable from context
- Summary: Dense 2-3 sentences with SPECIFICS (not generic descriptions - include actual content)
- Key points: 3-5 bullets capturing concrete value
- Frameworks used: Any frameworks referenced in this section
- Notable quotes: Best 1-2 quotes from this section

## 12. SOURCES REFERENCED
Papers, books, podcasts, links, tools, communities mentioned.
Type: paper/book/podcast/link/discord/community/event

## 13. PEOPLE & COMMUNITIES
People, organizations, events, communities referenced.
Include roles and affiliations where identifiable.

## 14. CONCEPTS MENTIONED
Key concepts and ideas with descriptions and relevance to the video.

## 15. DETAILED INSIGHTS (3-4 paragraphs)
Extended analysis that:
- Connects the dots between sections and ideas
- Identifies implications not explicitly stated
- Notes what's missing or could be challenged
- Provides synthesis that adds value beyond summarizing

## 16. CONFIDENCE SCORES
Rate your confidence (0.0-1.0) for each extraction category:
tldr, teaser_hooks, keywords, core_topics, lessons_learned, direct_quotes, 
analogies_metaphors, frameworks_shared, statistics_data, section_analysis,
sources_referenced, people_mentioned, communities_mentioned, concepts_mentioned, detailed_insights

---

QUALITY STANDARDS:
- Quotes must be EXACT or near-exact from transcript - verbatim
- Numbers must be PRECISE as stated - don't round or approximate
- Frameworks must be ACTIONABLE descriptions - someone could apply them
- Teasers must create GENUINE curiosity - not clickbait, real value
- Sections must have SPECIFIC content - not generic summaries
- Every extraction must convey VALUE and SIGNAL - no filler"""
            }
        ]

        return opik.ChatPrompt(
            name="video-master-extraction",
            messages=messages,
            metadata={
                "category": "video-analysis",
                "output_schema": "VideoAnalysisResponse",
                "version": VideoAnalysisPrompts.CURRENT_VERSION,
                "extraction_type": "comprehensive-v2",
                "changes": [
                    "Added direct_quotes extraction (5-10 verbatim aha moments)",
                    "Added analogies_metaphors extraction",
                    "Added frameworks_shared extraction",
                    "Added statistics_data extraction",
                    "Added section_analysis deep dive",
                    "Added teaser_hooks (3 sentences)",
                    "Added keywords extraction (8-15 tags)",
                    "Full transcript processing (no truncation)",
                    "Enhanced prompt for density and precision"
                ]
            }
        )
```

---

## Phase 3: Remove Transcript Truncation

### File: `src/app/agents/video_analyzer/nodes.py`

#### 3.1 Remove Truncation in `master_extraction_node`

**Location**: Line ~103

**Before:**
```python
"transcript": transcript["text"][:12000]
```

**After:**
```python
"transcript": transcript["text"]  # Full transcript - no truncation
```

#### 3.2 Update ProcessingMetrics Version

**Location**: Line ~167

**Before:**
```python
metrics = ProcessingMetrics(
    workflow_version="1.2",
```

**After:**
```python
metrics = ProcessingMetrics(
    workflow_version="2.0",
```

#### 3.3 Update Extraction Completeness Tracking

**Location**: Line ~177-186

**Before:**
```python
extraction_completeness={
    "tldr": bool(parsed_response.tldr),
    "core_topics": bool(parsed_response.core_topics),
    "lessons_learned": bool(parsed_response.lessons_learned),
    "sources_referenced": bool(parsed_response.sources_referenced),
    "concepts_mentioned": bool(parsed_response.concepts_mentioned),
    "people_mentioned": bool(parsed_response.people_mentioned),
    "communities_mentioned": bool(parsed_response.communities_mentioned),
    "detailed_insights": bool(parsed_response.detailed_insights)
}
```

**After:**
```python
extraction_completeness={
    "tldr": bool(parsed_response.tldr),
    "teaser_hooks": bool(parsed_response.teaser_hooks),
    "keywords": bool(parsed_response.keywords),
    "core_topics": bool(parsed_response.core_topics),
    "lessons_learned": bool(parsed_response.lessons_learned),
    "sources_referenced": bool(parsed_response.sources_referenced),
    "concepts_mentioned": bool(parsed_response.concepts_mentioned),
    "people_mentioned": bool(parsed_response.people_mentioned),
    "communities_mentioned": bool(parsed_response.communities_mentioned),
    "direct_quotes": bool(parsed_response.direct_quotes),
    "analogies_metaphors": bool(parsed_response.analogies_metaphors),
    "frameworks_shared": bool(parsed_response.frameworks_shared),
    "statistics_data": bool(parsed_response.statistics_data),
    "section_analysis": bool(parsed_response.section_analysis),
    "detailed_insights": bool(parsed_response.detailed_insights)
}
```

---

## Phase 4: Update Save Results Node

### File: `src/app/agents/video_analyzer/nodes.py`

#### 4.1 Update `save_results_node` Function

**Location**: Line ~240-269

**Update the `VideoAnalysisComplete` construction to include new fields:**

```python
complete_analysis = VideoAnalysisComplete(
    video_id=state["video_id"],
    tldr=response.tldr,
    key_audience=response.key_audience,
    teaser_hooks=response.teaser_hooks,  # NEW
    keywords=response.keywords,  # NEW
    core_topics=[topic.model_dump() for topic in response.core_topics],
    lessons_learned=response.lessons_learned,
    detailed_insights=response.detailed_insights,
    sources_referenced=[source.model_dump() for source in response.sources_referenced],
    concepts_mentioned=[concept.model_dump() for concept in response.concepts_mentioned],
    people_mentioned=[person.model_dump() for person in response.people_mentioned],
    communities_mentioned=[community.model_dump() for community in response.communities_mentioned],
    direct_quotes=[q.model_dump() for q in response.direct_quotes],  # NEW
    analogies_metaphors=[a.model_dump() for a in response.analogies_metaphors],  # NEW
    frameworks_shared=[f.model_dump() for f in response.frameworks_shared],  # NEW
    statistics_data=[s.model_dump() for s in response.statistics_data],  # NEW
    section_analysis=[sec.model_dump() for sec in response.section_analysis],  # NEW
    metadata_extracted={
        "video": video or {},
        "channel": channel or {},
        "workflow_metadata": metrics.model_dump(mode='json')
    },
    input_tokens=metrics.input_tokens,
    output_tokens=metrics.output_tokens,
    total_tokens=metrics.input_tokens + metrics.output_tokens,
    total_cost=metrics.total_cost,
    total_processing_time_seconds=metrics.processing_time_seconds,
    confidence_scores=response.confidence_scores,
    processing_metadata={
        "extraction_method": metrics.extraction_method,
        "workflow_version": metrics.workflow_version,
        "opik_trace_id": None
    },
    model_name=settings.analysis_model_name,
    processed_at=datetime.now(timezone.utc)
)
```

---

## Phase 5: Update Workflow

### File: `src/app/agents/video_analyzer/workflow.py`

#### 5.1 Update `analyze_video` Function

**Location**: Line ~81-99

**Update the `VideoAnalysisComplete` construction:**

```python
complete_analysis = VideoAnalysisComplete(
    video_id=video_id,
    tldr=response.tldr,
    key_audience=response.key_audience,
    teaser_hooks=response.teaser_hooks,  # NEW
    keywords=response.keywords,  # NEW
    core_topics=[topic.model_dump() for topic in response.core_topics],
    lessons_learned=response.lessons_learned,
    detailed_insights=response.detailed_insights,
    sources_referenced=[source.model_dump() for source in response.sources_referenced],
    concepts_mentioned=[concept.model_dump() for concept in response.concepts_mentioned],
    people_mentioned=[person.model_dump() for person in response.people_mentioned],
    communities_mentioned=[community.model_dump() for community in response.communities_mentioned],
    direct_quotes=[q.model_dump() for q in response.direct_quotes],  # NEW
    analogies_metaphors=[a.model_dump() for a in response.analogies_metaphors],  # NEW
    frameworks_shared=[f.model_dump() for f in response.frameworks_shared],  # NEW
    statistics_data=[s.model_dump() for s in response.statistics_data],  # NEW
    section_analysis=[sec.model_dump() for sec in response.section_analysis],  # NEW
    metadata_extracted=final_state.get("video", {}),
    input_tokens=metrics.input_tokens,
    output_tokens=metrics.output_tokens,
    total_tokens=metrics.input_tokens + metrics.output_tokens,
    total_cost=metrics.total_cost,
    total_processing_time_seconds=metrics.processing_time_seconds,
    confidence_scores=response.confidence_scores,
    model_name=settings.analysis_model_name
)
```

#### 5.2 Update Workflow Tags

**Location**: Line ~42

**Before:**
```python
tags=["video", "analysis", settings.analysis_model_name, "single-master-prompt"]
```

**After:**
```python
tags=["video", "analysis", settings.analysis_model_name, "single-master-prompt", "v2.0"]
```

---

## Phase 6: Update Repository

### File: `src/app/repositories/video_analysis_repository.py`

#### 6.1 Update `save_analysis` Method

**Location**: Line ~41-65

**Add new fields to the data dict:**

```python
data = {
    "video_id": analysis.video_id,
    "summary": analysis.tldr,
    "analysis": analysis.detailed_insights,
    "key_points": [f"{topic['topic']} ({topic['category']})" for topic in analysis.core_topics],
    "tags": self._extract_tags(analysis),
    "tldr": analysis.tldr,
    "core_topics": analysis.core_topics,
    "lessons_learned": analysis.lessons_learned,
    "detailed_insights": analysis.detailed_insights,
    "sources_referenced": analysis.sources_referenced,
    "concepts_mentioned": analysis.concepts_mentioned,
    "people_mentioned": analysis.people_mentioned,
    "communities_mentioned": analysis.communities_mentioned,
    # === NEW V2 FIELDS ===
    "teaser_hooks": analysis.teaser_hooks,
    "keywords": analysis.keywords,
    "direct_quotes": analysis.direct_quotes,
    "analogies_metaphors": analysis.analogies_metaphors,
    "frameworks_shared": analysis.frameworks_shared,
    "statistics_data": analysis.statistics_data,
    "section_analysis": analysis.section_analysis,
    # === END NEW FIELDS ===
    "metadata_extracted": analysis.metadata_extracted,
    "input_tokens": analysis.input_tokens,
    "output_tokens": analysis.output_tokens,
    "total_tokens": analysis.total_tokens,
    "total_cost": analysis.total_cost,
    "total_processing_time_seconds": analysis.total_processing_time_seconds,
    "processing_metadata": analysis.processing_metadata,
    "model_name": analysis.model_name,
    "tokens_used": analysis.total_tokens,
    "processed_at": analysis.processed_at.isoformat() if analysis.processed_at else datetime.now(timezone.utc).isoformat()
}
```

#### 6.2 Update `get_analysis` Method

**Location**: Line ~111-132

**Add new fields to the reconstruction:**

```python
return VideoAnalysisComplete(
    video_id=row['video_id'],
    tldr=row.get('tldr', ''),
    key_audience="",  # Not stored separately
    teaser_hooks=row.get('teaser_hooks') or [],  # NEW
    keywords=row.get('keywords') or [],  # NEW
    core_topics=row.get('core_topics') or [],
    lessons_learned=row.get('lessons_learned') or {},
    detailed_insights=row.get('detailed_insights', ''),
    sources_referenced=row.get('sources_referenced') or [],
    concepts_mentioned=row.get('concepts_mentioned') or [],
    people_mentioned=row.get('people_mentioned') or [],
    communities_mentioned=row.get('communities_mentioned') or [],
    direct_quotes=row.get('direct_quotes') or [],  # NEW
    analogies_metaphors=row.get('analogies_metaphors') or [],  # NEW
    frameworks_shared=row.get('frameworks_shared') or [],  # NEW
    statistics_data=row.get('statistics_data') or [],  # NEW
    section_analysis=row.get('section_analysis') or [],  # NEW
    metadata_extracted=row.get('metadata_extracted') or {},
    input_tokens=row.get('input_tokens') or 0,
    output_tokens=row.get('output_tokens') or 0,
    total_tokens=row.get('total_tokens') or 0,
    total_cost=float(row['total_cost']) if row.get('total_cost') else 0.0,
    total_processing_time_seconds=float(row['total_processing_time_seconds']) if row.get('total_processing_time_seconds') else 0.0,
    confidence_scores={},
    processing_metadata=row.get('processing_metadata'),
    model_name=row.get('model_name') or "unknown",
    processed_at=datetime.fromisoformat(row['processed_at']) if row.get('processed_at') else datetime.now(timezone.utc)
)
```

#### 6.3 Update `_extract_tags` Method

**Location**: Line ~206-224

**Enhance tag extraction with new fields:**

```python
def _extract_tags(self, analysis: VideoAnalysisComplete) -> list:
    """Extract tags from analysis for the legacy tags field."""
    tags = []

    # Add keywords directly (new in V2)
    if hasattr(analysis, 'keywords') and analysis.keywords:
        tags.extend(analysis.keywords)

    # Add topic categories as tags
    for topic in analysis.core_topics:
        if isinstance(topic, dict):
            tags.append(topic.get('category', 'general'))
            tags.append(topic.get('topic', '').lower().replace(' ', '-'))

    # Add concept tags
    for concept in analysis.concepts_mentioned:
        if isinstance(concept, dict):
            concept_name = concept.get('concept', '').lower().replace(' ', '-')
            if concept_name:
                tags.append(concept_name)

    # Add framework names (new in V2)
    if hasattr(analysis, 'frameworks_shared'):
        for framework in analysis.frameworks_shared:
            if isinstance(framework, dict):
                fw_name = framework.get('name', '').lower().replace(' ', '-')
                if fw_name:
                    tags.append(fw_name)

    # Remove duplicates and limit
    return list(set(tags))[:20]  # Increased from 15 to 20
```

---

## Phase 7: Database Migration

### File: `supabase/migrations/20250101000000_video_analysis_v2.sql`

**Create new migration file:**

```sql
-- Video Analysis V2 Schema Enhancement
-- Adds deep extraction fields for quotes, frameworks, statistics, and section analysis

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
```

---

## Implementation Checklist

### Phase 1: Models (15 min)
- [ ] Add `DirectQuote` model to `video_analysis.py`
- [ ] Add `AnalogyMetaphor` model to `video_analysis.py`
- [ ] Add `FrameworkMentioned` model to `video_analysis.py`
- [ ] Add `StatisticDataPoint` model to `video_analysis.py`
- [ ] Add `VideoSection` model to `video_analysis.py`
- [ ] Update `VideoAnalysisResponse` with new fields
- [ ] Update `VideoAnalysisComplete` with new fields

### Phase 2: Prompt (10 min)
- [ ] Replace `prompts.py` with V2 prompt
- [ ] Verify prompt formatting is correct

### Phase 3: Remove Truncation (5 min)
- [ ] Remove `[:12000]` from transcript in `nodes.py`
- [ ] Update workflow version to "2.0"
- [ ] Update extraction completeness tracking

### Phase 4: Save Results Node (10 min)
- [ ] Update `save_results_node` to map new fields
- [ ] Verify all new fields are serialized correctly

### Phase 5: Workflow (5 min)
- [ ] Update `analyze_video` function in `workflow.py`
- [ ] Update workflow tags to include "v2.0"

### Phase 6: Repository (15 min)
- [ ] Update `save_analysis` with new fields
- [ ] Update `get_analysis` with new fields
- [ ] Update `_extract_tags` to use keywords

### Phase 7: Database (5 min)
- [ ] Create migration file
- [ ] Apply migration to Supabase

### Phase 8: Testing (30 min)
- [ ] Test single video analysis
- [ ] Verify all new fields are extracted
- [ ] Check database has new columns populated
- [ ] Verify no truncation (full transcript processed)
- [ ] Check token usage increase (expected ~2-3x)

---

## Expected Changes

### Token Usage
| Metric | V1.1 | V2.0 (Expected) |
|--------|------|-----------------|
| Input tokens | ~6,800 | ~15,000-20,000 (full transcript) |
| Output tokens | ~3,000 | ~5,000-8,000 (more extractions) |
| Total cost | ~$0.0014 | ~$0.004-0.006 |
| Processing time | ~18s | ~30-45s |

### Extraction Depth
| Field | V1.1 | V2.0 |
|-------|------|------|
| Quotes | ❌ None | ✅ 5-10 verbatim |
| Analogies | ❌ None | ✅ All captured |
| Frameworks | ⚠️ In concepts | ✅ Dedicated extraction |
| Statistics | ❌ None | ✅ All numbers |
| Sections | ❌ None | ✅ 3-7 deep analyses |
| Teasers | ❌ None | ✅ 3 hooks |
| Keywords | ❌ None | ✅ 8-15 tags |

---

## Rollback Plan

If V2 extraction causes issues:

1. **Revert prompt**: Change `CURRENT_VERSION` back to "1.1" and restore old prompt
2. **Re-add truncation**: Add back `[:12000]` to transcript
3. **Fields are additive**: Old data still works, new fields just stay empty

---

## Future Considerations

### Opik Prompt Library Migration

When ready to use Opik's cloud prompt library:

```python
# Instead of local prompt creation:
def get_master_extraction_prompt() -> opik.ChatPrompt:
    # Fetch from Opik cloud
    return opik.get_prompt(
        name="video-master-extraction",
        version=2  # Pin to V2
    )
```

**Benefits:**
- A/B test different prompt versions without deploy
- Rollback prompts instantly
- Track prompt performance in Opik dashboard
- Collaborate on prompts across team

### Digest Integration

The new fields enable richer digest generation:

```python
# Example digest section using V2 fields
def generate_digest_section(analysis: VideoAnalysisComplete) -> str:
    # Use teasers for email subject/preview
    teaser = analysis.teaser_hooks[0] if analysis.teaser_hooks else analysis.tldr[:100]
    
    # Use best quotes for highlights
    top_quotes = [q['quote'] for q in analysis.direct_quotes[:3]]
    
    # Use statistics for credibility
    key_stats = [s['value'] for s in analysis.statistics_data[:3]]
    
    # Use frameworks for actionable value
    frameworks = [f['name'] for f in analysis.frameworks_shared]
```

---

## Files Summary

### Files to UPDATE

| File | Changes |
|------|---------|
| `src/app/models/video_analysis.py` | Add 5 new models, update 2 existing |
| `src/app/agents/video_analyzer/prompts.py` | Complete V2 prompt replacement |
| `src/app/agents/video_analyzer/nodes.py` | Remove truncation, update mappings |
| `src/app/agents/video_analyzer/workflow.py` | Update field mappings, tags |
| `src/app/repositories/video_analysis_repository.py` | Add new fields to save/get |

### Files to CREATE

| File | Purpose |
|------|---------|
| `supabase/migrations/20250101000000_video_analysis_v2.sql` | Add 7 new JSONB columns |

---

## Success Criteria

- [ ] Full transcript processed (no truncation)
- [ ] 5-10 direct quotes extracted per video
- [ ] Analogies/metaphors captured
- [ ] Frameworks identified with actionable descriptions
- [ ] Statistics extracted with context
- [ ] Section analysis provides dense summaries
- [ ] 3 teaser hooks generated
- [ ] 8-15 keywords extracted
- [ ] All new fields saved to database
- [ ] Digest can use new fields for richer output


