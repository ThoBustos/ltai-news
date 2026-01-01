"""Formatters for rendering digest content to Markdown and HTML - V2.0.

V2 Changes:
- Zero emojis throughout
- No thumbnails
- Table of contents navigation
- Estimated read time
- Expanded video sections with V2 depth fields
- Clean, professional styling
"""

from typing import List
from datetime import date

from app.models.daily_digest import (
    DigestContentResponse,
    VideoSection,
    ActionItem,
    ContrarianCorner,
    ReferencesIndex,
    ReferenceItem,
)


def format_digest_markdown(content: DigestContentResponse, target_date: date) -> str:
    """Format digest content as Markdown - V2 Clean Professional.

    Args:
        content: DigestContentResponse from LLM
        target_date: Date of the digest

    Returns:
        Formatted Markdown string
    """
    lines = []

    # Header - NO emoji
    lines.append(f"# {content.title}")
    lines.append("")
    lines.append(f"**{target_date.strftime('%B %d, %Y')}**")
    lines.append("")

    # Stats with read time
    stats = content.stats
    lines.append("---")
    lines.append(f"**{stats.video_count} videos** | **{stats.total_duration_minutes} min watch time** | **{stats.estimated_read_minutes} min read**")
    if stats.channels:
        channel_list = ", ".join([f"{c.channel_name} ({c.video_count})" for c in stats.channels])
        lines.append(f"*Sources: {channel_list}*")
    lines.append("---")
    lines.append("")

    # Table of Contents
    lines.append("## Contents")
    lines.append("")
    for i, toc_item in enumerate(content.table_of_contents):
        # Create anchor-friendly slug
        slug = toc_item.lower().replace(" ", "-").replace(":", "").replace("'", "")
        lines.append(f"{i+1}. [{toc_item}](#{slug})")
    lines.append("")

    # Daily TLDR / Overview
    lines.append("---")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(content.daily_tldr)
    lines.append("")

    # Video Sections - NO thumbnails
    lines.append("---")
    lines.append("")
    lines.append("## Video Breakdowns")
    lines.append("")

    for video in content.video_sections:
        lines.extend(_format_video_section_markdown_v2(video))
        lines.append("")

    # Contrarian Corner - NO emoji
    lines.append("---")
    lines.append("")
    lines.append("## Contrarian Corner")
    lines.append("")
    lines.extend(_format_contrarian_markdown_v2(content.contrarian_corner))
    lines.append("")

    # Action Items - NO emoji
    lines.append("---")
    lines.append("")
    lines.append("## Action Items")
    lines.append("")
    for item in content.action_items:
        difficulty_label = f"[{item.difficulty}]"
        lines.append(f"- **{item.action}** {difficulty_label}")
        lines.append(f"  - {item.context}")
    lines.append("")

    # References Index - NO emoji headers
    lines.append("---")
    lines.append("")
    lines.append("## References")
    lines.append("")
    lines.extend(_format_references_markdown_v2(content.references_index))
    lines.append("")

    # Conclusion - NO emoji
    lines.append("---")
    lines.append("")
    lines.append("## Final Thought")
    lines.append("")
    lines.append(f"*{content.conclusion}*")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    keywords_str = " | ".join(content.keywords)
    lines.append(f"**Keywords:** {keywords_str}")
    lines.append("")

    return "\n".join(lines)


def _format_video_section_markdown_v2(video: VideoSection) -> List[str]:
    """Format a single video section - V2 with depth fields, no thumbnail."""
    lines = []

    # Title and metadata
    lines.append(f"### [{video.title}]({video.video_url})")
    lines.append(f"*{video.channel_name}* | {video.duration_minutes} min")
    if video.speakers:
        lines.append(f"*Speakers: {', '.join(video.speakers)}*")
    if video.tags:
        lines.append(f"Tags: {', '.join(video.tags)}")
    lines.append("")

    # Condensed summary
    lines.append(f"**Summary:** {video.condensed_summary}")
    lines.append("")

    # Structure overview
    if video.structure_overview:
        lines.append(f"**Structure:** {video.structure_overview}")
        lines.append("")

    # Key quotes
    if video.key_quotes:
        lines.append("**Key Quotes:**")
        for quote in video.key_quotes:
            lines.append(f'> "{quote}"')
        lines.append("")

    # Frameworks
    if video.frameworks_mentioned:
        lines.append(f"**Frameworks:** {', '.join(video.frameworks_mentioned)}")
        lines.append("")

    # Statistics
    if video.key_statistics:
        lines.append("**Key Numbers:**")
        for stat in video.key_statistics:
            lines.append(f"- {stat}")
        lines.append("")

    # Analogies
    if video.key_analogies:
        lines.append("**Analogies:**")
        for analogy in video.key_analogies:
            lines.append(f"- {analogy}")
        lines.append("")

    # Cross-video connections
    if video.connections:
        lines.append("**Connections:**")
        for conn in video.connections:
            lines.append(f"- {conn}")
        lines.append("")

    # Deep analysis
    lines.append("**Deep Dive:**")
    lines.append("")
    lines.append(video.deep_analysis)
    lines.append("")

    return lines


def _format_contrarian_markdown_v2(contrarian: ContrarianCorner) -> List[str]:
    """Format contrarian corner - V2 no emoji."""
    lines = []
    lines.append(f"> **{contrarian.insight}**")
    lines.append("")
    lines.append(f"*Why this challenges common wisdom:* {contrarian.why_counterintuitive}")
    return lines


def _format_references_markdown_v2(refs: ReferencesIndex) -> List[str]:
    """Format references index - V2 no emoji headers."""
    lines = []

    def format_ref_list(title: str, items: List[ReferenceItem]):
        if not items:
            return []
        result = [f"### {title}"]
        for ref in items:
            if ref.url:
                result.append(f"- [{ref.name}]({ref.url})" + (f" by {ref.author}" if ref.author else ""))
            else:
                result.append(f"- {ref.name}" + (f" by {ref.author}" if ref.author else ""))
            if ref.description:
                result.append(f"  - {ref.description}")
        result.append("")
        return result

    lines.extend(format_ref_list("Books", refs.books))
    lines.extend(format_ref_list("Papers", refs.papers))
    lines.extend(format_ref_list("Frameworks", refs.frameworks))
    lines.extend(format_ref_list("Concepts", refs.concepts))
    lines.extend(format_ref_list("People", refs.people))
    lines.extend(format_ref_list("Communities", refs.communities))

    return lines


def format_digest_html(content: DigestContentResponse, target_date: date) -> str:
    """Format digest content as HTML - V2 Clean Professional.

    Args:
        content: DigestContentResponse from LLM
        target_date: Date of the digest

    Returns:
        Formatted HTML string
    """
    # Build TOC HTML
    def make_anchor(text: str) -> str:
        """Create a URL-safe anchor from text."""
        return text.lower().replace(" ", "-").replace(":", "").replace("'", "")

    toc_items = "".join([
        f'<li><a href="#{make_anchor(item)}">{item}</a></li>'
        for item in content.table_of_contents
    ])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{content.title}</title>
    <style>
        body {{
            font-family: Georgia, 'Times New Roman', serif;
            line-height: 1.7;
            color: #1a1a1a;
            max-width: 720px;
            margin: 0 auto;
            padding: 24px;
            background-color: #fafafa;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 4px;
            padding: 40px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }}
        h1 {{
            font-size: 26px;
            margin-bottom: 8px;
            color: #111;
            font-weight: 600;
            line-height: 1.3;
        }}
        h2 {{
            font-size: 20px;
            margin-top: 36px;
            color: #222;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 8px;
            font-weight: 600;
        }}
        h3 {{
            font-size: 17px;
            margin-top: 28px;
            color: #333;
            font-weight: 600;
        }}
        .date {{
            color: #666;
            font-size: 14px;
            margin-bottom: 16px;
        }}
        .stats {{
            background-color: #f5f5f5;
            padding: 16px 20px;
            border-radius: 4px;
            margin: 20px 0;
            border-left: 3px solid #333;
        }}
        .stats-main {{
            font-size: 15px;
            font-weight: 600;
            color: #111;
        }}
        .stats-sources {{
            font-size: 14px;
            color: #555;
            font-style: italic;
            margin-top: 6px;
        }}
        .toc {{
            background-color: #fafafa;
            padding: 16px 20px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .toc h4 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .toc ol {{
            margin: 0;
            padding-left: 20px;
        }}
        .toc li {{
            margin: 4px 0;
        }}
        .toc a {{
            color: #2563eb;
            text-decoration: none;
        }}
        .toc a:hover {{
            text-decoration: underline;
        }}
        .overview {{
            font-size: 16px;
            line-height: 1.8;
        }}
        .video-section {{
            border: 1px solid #e5e5e5;
            border-radius: 4px;
            padding: 24px;
            margin: 20px 0;
            background-color: #fefefe;
        }}
        .video-title {{
            font-size: 17px;
            font-weight: 600;
            color: #2563eb;
            text-decoration: none;
        }}
        .video-title:hover {{
            text-decoration: underline;
        }}
        .video-meta {{
            font-size: 14px;
            color: #666;
            margin: 6px 0;
            font-style: italic;
        }}
        .video-tags {{
            font-size: 13px;
            color: #888;
            margin: 8px 0;
        }}
        .video-summary {{
            margin: 16px 0;
            font-size: 15px;
        }}
        .quote {{
            background-color: #f9f9f9;
            border-left: 3px solid #ccc;
            padding: 12px 16px;
            margin: 12px 0;
            font-style: italic;
            color: #444;
        }}
        .frameworks, .statistics, .analogies, .connections {{
            margin: 12px 0;
            font-size: 14px;
        }}
        .deep-dive {{
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid #eee;
        }}
        .deep-dive h4 {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }}
        .contrarian {{
            background-color: #fff8f0;
            border: 1px solid #ffe0c0;
            border-radius: 4px;
            padding: 20px;
            margin: 20px 0;
        }}
        .contrarian-insight {{
            font-size: 16px;
            font-weight: 600;
            color: #8b4513;
        }}
        .action-item {{
            padding: 12px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        .action-item:last-child {{
            border-bottom: none;
        }}
        .action-title {{
            font-weight: 600;
        }}
        .action-context {{
            font-size: 14px;
            color: #666;
            margin-top: 4px;
        }}
        .difficulty {{
            display: inline-block;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 3px;
            margin-left: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .difficulty-quick {{ background-color: #d4edda; color: #155724; }}
        .difficulty-medium {{ background-color: #fff3cd; color: #856404; }}
        .difficulty-deep-dive {{ background-color: #cce5ff; color: #004085; }}
        .references {{
            font-size: 14px;
        }}
        .ref-category {{
            margin-top: 16px;
        }}
        .ref-category h4 {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        .conclusion {{
            font-style: italic;
            font-size: 17px;
            color: #444;
            text-align: center;
            padding: 28px 20px;
            background-color: #fafafa;
            border-radius: 4px;
            margin: 24px 0;
        }}
        .keywords {{
            text-align: center;
            font-size: 12px;
            color: #888;
            margin-top: 20px;
        }}
        .keyword {{
            display: inline-block;
            background-color: #f0f0f0;
            padding: 3px 10px;
            border-radius: 3px;
            margin: 2px;
        }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: #999;
            margin-top: 32px;
            padding-top: 16px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{content.title}</h1>
        <p class="date">{target_date.strftime('%B %d, %Y')}</p>

        <div class="stats">
            <div class="stats-main">{content.stats.video_count} videos | {content.stats.total_duration_minutes} min watch time | {content.stats.estimated_read_minutes} min read</div>
            <div class="stats-sources">Sources: {', '.join([f"{c.channel_name} ({c.video_count})" for c in content.stats.channels])}</div>
        </div>

        <div class="toc">
            <h4>Contents</h4>
            <ol>{toc_items}</ol>
        </div>

        <h2 id="overview">Overview</h2>
        <div class="overview">{_html_paragraphs(content.daily_tldr)}</div>

        <h2 id="video-breakdowns">Video Breakdowns</h2>
        {_format_videos_html_v2(content.video_sections)}

        <h2 id="contrarian-corner">Contrarian Corner</h2>
        {_format_contrarian_html_v2(content.contrarian_corner)}

        <h2 id="actions">Action Items</h2>
        {_format_actions_html_v2(content.action_items)}

        <h2 id="references">References</h2>
        <div class="references">
            {_format_references_html_v2(content.references_index)}
        </div>

        <div class="conclusion">"{content.conclusion}"</div>

        <div class="keywords">
            {' '.join([f'<span class="keyword">{kw}</span>' for kw in content.keywords])}
        </div>

        <div class="footer">
            Generated with AI | Confidence: {content.confidence_score:.0%}
        </div>
    </div>
</body>
</html>"""

    return html


def _html_paragraphs(text: str) -> str:
    """Convert text with newlines to HTML paragraphs."""
    paragraphs = text.split("\n\n")
    return "".join([f"<p>{p.strip()}</p>" for p in paragraphs if p.strip()])


def _format_videos_html_v2(videos: List[VideoSection]) -> str:
    """Format video sections as HTML - V2 with depth fields, no thumbnail."""
    html_parts = []
    for video in videos:
        # Build quotes HTML
        quotes_html = ""
        if video.key_quotes:
            for quote in video.key_quotes:
                quotes_html += f'<div class="quote">"{quote}"</div>'

        # Build frameworks HTML
        frameworks_html = ""
        if video.frameworks_mentioned:
            frameworks_html = f'<div class="frameworks"><strong>Frameworks:</strong> {", ".join(video.frameworks_mentioned)}</div>'

        # Build statistics HTML
        stats_html = ""
        if video.key_statistics:
            stats_items = "".join([f"<li>{s}</li>" for s in video.key_statistics])
            stats_html = f'<div class="statistics"><strong>Key Numbers:</strong><ul>{stats_items}</ul></div>'

        # Build analogies HTML
        analogies_html = ""
        if video.key_analogies:
            analogies_items = "".join([f"<li>{a}</li>" for a in video.key_analogies])
            analogies_html = f'<div class="analogies"><strong>Analogies:</strong><ul>{analogies_items}</ul></div>'

        # Build connections HTML
        connections_html = ""
        if video.connections:
            connections_items = "".join([f"<li>{c}</li>" for c in video.connections])
            connections_html = f'<div class="connections"><strong>Connections:</strong><ul>{connections_items}</ul></div>'

        # Build speakers and tags
        speakers_html = f'<div class="video-meta">Speakers: {", ".join(video.speakers)}</div>' if video.speakers else ""
        tags_html = f'<div class="video-tags">Tags: {", ".join(video.tags)}</div>' if video.tags else ""
        structure_html = f'<p><strong>Structure:</strong> {video.structure_overview}</p>' if video.structure_overview else ""

        html_parts.append(f"""
        <div class="video-section">
            <a href="{video.video_url}" class="video-title">{video.title}</a>
            <div class="video-meta">{video.channel_name} | {video.duration_minutes} min</div>
            {speakers_html}
            {tags_html}

            <div class="video-summary"><strong>Summary:</strong> {video.condensed_summary}</div>
            {structure_html}

            {quotes_html}
            {frameworks_html}
            {stats_html}
            {analogies_html}
            {connections_html}

            <div class="deep-dive">
                <h4>Deep Dive</h4>
                {_html_paragraphs(video.deep_analysis)}
            </div>
        </div>
        """)
    return "".join(html_parts)


def _format_contrarian_html_v2(contrarian: ContrarianCorner) -> str:
    """Format contrarian corner as HTML - V2 no emoji."""
    return f"""
    <div class="contrarian">
        <p class="contrarian-insight">{contrarian.insight}</p>
        <p><em>Why this challenges common wisdom:</em> {contrarian.why_counterintuitive}</p>
    </div>
    """


def _format_actions_html_v2(actions: List[ActionItem]) -> str:
    """Format action items as HTML - V2 no emoji."""
    html_parts = []
    for item in actions:
        difficulty_class = f"difficulty-{item.difficulty}"
        html_parts.append(f"""
        <div class="action-item">
            <span class="action-title">{item.action}</span>
            <span class="difficulty {difficulty_class}">{item.difficulty}</span>
            <p class="action-context">{item.context}</p>
        </div>
        """)
    return "".join(html_parts)


def _format_references_html_v2(refs: ReferencesIndex) -> str:
    """Format references as HTML - V2 no emoji."""
    html_parts = []

    def format_category(title: str, items: List[ReferenceItem]):
        if not items:
            return ""
        items_html = "<ul>"
        for ref in items:
            if ref.url:
                items_html += f'<li><a href="{ref.url}">{ref.name}</a>'
            else:
                items_html += f"<li>{ref.name}"
            if ref.author:
                items_html += f" by {ref.author}"
            if ref.description:
                items_html += f" - {ref.description}"
            items_html += "</li>"
        items_html += "</ul>"
        return f'<div class="ref-category"><h4>{title}</h4>{items_html}</div>'

    html_parts.append(format_category("Books", refs.books))
    html_parts.append(format_category("Papers", refs.papers))
    html_parts.append(format_category("Frameworks", refs.frameworks))
    html_parts.append(format_category("Concepts", refs.concepts))
    html_parts.append(format_category("People", refs.people))
    html_parts.append(format_category("Communities", refs.communities))

    return "".join(html_parts)
