"""Prompt management for video analysis using Opik ChatPrompt."""

from typing import Any, Dict, List
import opik


class VideoAnalysisPrompts:
    """Centralized prompt management using Opik ChatPrompt system."""

    @staticmethod
    def get_master_extraction_prompt() -> opik.ChatPrompt:
        """Get comprehensive analysis prompt with structured output schema."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": """You are an expert at analyzing technical videos and extracting comprehensive insights.

Your task is to analyze the video content and extract ALL the following information in a single structured response:
- TLDR summary (1-2 paragraphs)
- Core topics and their categories
- Lessons learned (technical, business, general)
- Sources referenced (papers, books, podcasts, links)
- Key concepts mentioned
- People and communities mentioned
- Overall insights and analysis

IMPORTANT: Respond with valid JSON only. No additional text before or after the JSON."""
            },
            {
                "role": "user",
                "content": """VIDEO TITLE: {{title}}
VIDEO DESCRIPTION: {{description}}
CHANNEL: {{channel_name}}
VIDEO URL: {{url}}
PUBLISHED AT: {{published_at}}
RAW METADATA: {{raw_metadata}}
TRANSCRIPT: {{transcript}}

Analyze this video comprehensively and extract:

1. TLDR: Create a 1-2 paragraph summary capturing the main purpose, key insights, and target audience
2. CORE TOPICS: Identify 3-7 main topics with categories (technical/business/philosophy/general) and importance levels
3. LESSONS LEARNED: Extract actionable lessons organized by category (technical/business/general)
4. SOURCES: Identify any papers, books, podcasts, links, or external references mentioned
5. CONCEPTS: Extract key concepts, frameworks, or ideas discussed
6. PEOPLE & COMMUNITIES: Note any people, organizations, communities, events, or Discord servers mentioned
7. INSIGHTS: Provide detailed analysis of the video's value and implications

Provide confidence scores (0.0-1.0) for each extraction category."""
            }
        ]

        return opik.ChatPrompt(
            name="video-master-extraction",
            messages=messages,
            metadata={
                "category": "video-analysis",
                "output_schema": "VideoAnalysisResponse",
                "version": "1.1",
                "extraction_type": "comprehensive"
            }
        )
