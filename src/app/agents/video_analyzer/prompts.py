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
