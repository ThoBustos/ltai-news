"""Formatters for rendering V2 weekly digest content to Markdown and HTML.

V2 Layout - High-signal, minimalist format.
"""

from datetime import date
from typing import List

from app.models.weekly_digest import WeeklyContentResponse


def format_weekly_markdown(content: WeeklyContentResponse, week_start: date, week_end: date) -> str:
    """Format V2 weekly digest content as Markdown.

    Args:
        content: WeeklyContentResponse from LLM
        week_start: Monday of the week
        week_end: Sunday of the week

    Returns:
        Formatted Markdown string
    """
    lines = []
    stats = content.stats
    date_range = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"

    # Header
    lines.append(f"# LTAI WEEKLY | {date_range}")
    lines.append(f"{stats.total_videos} videos | {stats.days_covered} days | {len(stats.channels)} channels")
    lines.append("")
    lines.append("---")
    lines.append("")

    # THE ONE THING
    lines.append("## THE ONE THING")
    lines.append("")
    lines.append(f"**{content.the_one_thing.headline}**")
    lines.append("")
    lines.append(content.the_one_thing.subtext)
    lines.append("")
    lines.append("---")
    lines.append("")

    # QUOTE OF THE WEEK
    lines.append("## QUOTE OF THE WEEK")
    lines.append("")
    lines.append(f"> \"{content.quote_of_the_week.text}\"")
    lines.append(f"> -- {content.quote_of_the_week.speaker}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # WATCH ONE
    watch = content.watch_one
    video_url = f"https://youtube.com/watch?v={watch.video_id}"
    lines.append("## WATCH IF YOU ONLY WATCH ONE")
    lines.append("")
    lines.append(f"**[{watch.title}]({video_url})**")
    lines.append(f"{watch.channel} | {watch.duration_minutes} min")
    lines.append("")
    lines.append(f"Why: {watch.why}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # NUMBERS THAT MATTER
    lines.append("## NUMBERS THAT MATTER")
    lines.append("")
    if content.numbers_that_matter:
        # Format as table
        numbers = content.numbers_that_matter[:3]
        num_row = "| " + " | ".join([n.number for n in numbers]) + " |"
        ctx_row = "| " + " | ".join([n.context for n in numbers]) + " |"
        sep_row = "| " + " | ".join(["---"] * len(numbers)) + " |"
        lines.append(num_row)
        lines.append(sep_row)
        lines.append(ctx_row)
    lines.append("")
    lines.append("---")
    lines.append("")

    # CONTRARIAN TAKE
    lines.append("## CONTRARIAN TAKE")
    lines.append("")
    lines.append(f"**They say:** {content.contrarian_take.conventional}")
    lines.append("")
    lines.append(f"**Actually:** {content.contrarian_take.actual}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # CONCEPT OF THE WEEK
    concept = content.concept_of_the_week
    concept_title = concept.term
    if concept.full_name:
        concept_title = f"{concept.term} ({concept.full_name})"
    lines.append(f"## CONCEPT: {concept_title}")
    lines.append("")
    lines.append(concept.definition)
    lines.append("")
    lines.append("---")
    lines.append("")

    # THEMES
    theme_count = len(content.themes)
    lines.append(f"## {theme_count} THEMES THIS WEEK")
    lines.append("")
    for i, theme in enumerate(content.themes, 1):
        lines.append(f"{i}. **{theme.name}** ({theme.mention_count} videos) -- {theme.one_liner}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # VIDEOS BY CATEGORY
    lines.append("## ALL VIDEOS BY CATEGORY")
    lines.append("")
    for category, videos in content.videos_by_category.items():
        lines.append(f"### {category} ({len(videos)})")
        lines.append("")
        for v in videos:
            video_url = f"https://youtube.com/watch?v={v.video_id}"
            lines.append(f"- **[{v.title}]({video_url})** -- {v.channel} | {v.day} | {v.duration_minutes}m")
            lines.append(f"  {v.one_liner}")
            lines.append("")
    lines.append("---")
    lines.append("")

    # WEEKLY NOTE
    lines.append("## WEEKLY NOTE")
    lines.append("")
    lines.append(f"*{content.weekly_note}*")
    lines.append("")

    return "\n".join(lines)


def format_weekly_html(content: WeeklyContentResponse, week_start: date, week_end: date) -> str:
    """Format V2 weekly digest content as HTML for email.

    Args:
        content: WeeklyContentResponse from LLM
        week_start: Monday of the week
        week_end: Sunday of the week

    Returns:
        Formatted HTML string
    """
    stats = content.stats
    date_range = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"

    # Numbers table
    numbers_html = ""
    if content.numbers_that_matter:
        numbers = content.numbers_that_matter[:3]
        num_cells = "".join([f'<td class="number">{n.number}</td>' for n in numbers])
        ctx_cells = "".join([f'<td class="context">{n.context}</td>' for n in numbers])
        numbers_html = f"""
        <table class="numbers-table">
            <tr>{num_cells}</tr>
            <tr>{ctx_cells}</tr>
        </table>
        """

    # Themes list
    themes_html = ""
    for i, theme in enumerate(content.themes, 1):
        themes_html += f"""
        <div class="theme-item">
            <span class="theme-num">{i}.</span>
            <strong>{theme.name}</strong>
            <span class="theme-count">({theme.mention_count} videos)</span>
            <span class="theme-desc">-- {theme.one_liner}</span>
        </div>
        """

    # Videos by category
    categories_html = ""
    for category, videos in content.videos_by_category.items():
        videos_list = ""
        for v in videos:
            video_url = f"https://youtube.com/watch?v={v.video_id}"
            videos_list += f"""
            <div class="video-item">
                <a href="{video_url}" class="video-title">{v.title}</a>
                <span class="video-meta">{v.channel} | {v.day} | {v.duration_minutes}m</span>
                <p class="video-oneliner">{v.one_liner}</p>
            </div>
            """
        categories_html += f"""
        <div class="category">
            <h3>{category} <span class="count">({len(videos)})</span></h3>
            {videos_list}
        </div>
        """

    # Watch one section
    watch = content.watch_one
    watch_url = f"https://youtube.com/watch?v={watch.video_id}"

    # Concept section
    concept = content.concept_of_the_week
    concept_title = concept.term
    if concept.full_name:
        concept_title = f"{concept.term} <span class='full-name'>({concept.full_name})</span>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LTAI Weekly | {date_range}</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 640px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a1a 0%, #333 100%);
            color: #fff;
            padding: 32px 24px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
            margin-bottom: 8px;
        }}
        .header .stats {{
            font-size: 14px;
            color: #ccc;
        }}
        .section {{
            padding: 24px;
            border-bottom: 1px solid #eee;
        }}
        .section:last-child {{
            border-bottom: none;
        }}
        .section-title {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #666;
            margin-bottom: 12px;
        }}
        .one-thing h2 {{
            font-size: 22px;
            font-weight: 700;
            line-height: 1.3;
            margin-bottom: 8px;
            color: #111;
        }}
        .one-thing p {{
            font-size: 16px;
            color: #444;
        }}
        .quote {{
            background-color: #f8f8f8;
            padding: 20px 24px;
            border-left: 4px solid #333;
        }}
        .quote-text {{
            font-size: 18px;
            font-style: italic;
            color: #333;
            margin-bottom: 8px;
        }}
        .quote-author {{
            font-size: 14px;
            color: #666;
        }}
        .watch-one {{
            background-color: #fffbeb;
            border-left: 4px solid #f59e0b;
        }}
        .watch-one .video-title {{
            font-size: 18px;
            font-weight: 600;
            color: #111;
            text-decoration: none;
            display: block;
            margin-bottom: 4px;
        }}
        .watch-one .video-title:hover {{
            color: #2563eb;
        }}
        .watch-one .video-meta {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }}
        .watch-one .why {{
            font-size: 15px;
            color: #444;
        }}
        .numbers-table {{
            width: 100%;
            border-collapse: collapse;
            text-align: center;
        }}
        .numbers-table td {{
            padding: 12px;
            border: 1px solid #eee;
        }}
        .numbers-table .number {{
            font-size: 24px;
            font-weight: 700;
            color: #111;
        }}
        .numbers-table .context {{
            font-size: 13px;
            color: #666;
        }}
        .contrarian {{
            background-color: #fef2f2;
            border-left: 4px solid #ef4444;
        }}
        .contrarian .label {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            color: #666;
            margin-bottom: 4px;
        }}
        .contrarian .conventional {{
            font-size: 15px;
            color: #666;
            margin-bottom: 12px;
        }}
        .contrarian .actual {{
            font-size: 16px;
            font-weight: 500;
            color: #111;
        }}
        .concept {{
            background-color: #f0f9ff;
            border-left: 4px solid #3b82f6;
        }}
        .concept h3 {{
            font-size: 18px;
            font-weight: 600;
            color: #111;
            margin-bottom: 8px;
        }}
        .concept .full-name {{
            font-weight: 400;
            color: #666;
        }}
        .concept p {{
            font-size: 15px;
            color: #444;
        }}
        .theme-item {{
            margin-bottom: 8px;
            font-size: 15px;
        }}
        .theme-num {{
            color: #999;
            margin-right: 4px;
        }}
        .theme-count {{
            color: #666;
            font-size: 13px;
        }}
        .theme-desc {{
            color: #555;
        }}
        .category {{
            margin-bottom: 24px;
        }}
        .category h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #333;
            padding-bottom: 8px;
            border-bottom: 1px solid #eee;
            margin-bottom: 12px;
        }}
        .category .count {{
            font-weight: 400;
            color: #999;
        }}
        .video-item {{
            margin-bottom: 16px;
            padding-left: 12px;
            border-left: 2px solid #eee;
        }}
        .video-item .video-title {{
            font-size: 15px;
            font-weight: 500;
            color: #111;
            text-decoration: none;
        }}
        .video-item .video-title:hover {{
            color: #2563eb;
        }}
        .video-item .video-meta {{
            font-size: 13px;
            color: #888;
            display: block;
            margin: 2px 0;
        }}
        .video-item .video-oneliner {{
            font-size: 14px;
            color: #555;
            margin-top: 4px;
        }}
        .weekly-note {{
            background-color: #fafafa;
            text-align: center;
        }}
        .weekly-note p {{
            font-size: 16px;
            font-style: italic;
            color: #444;
            line-height: 1.7;
        }}
        .footer {{
            text-align: center;
            padding: 16px;
            font-size: 12px;
            color: #999;
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LTAI WEEKLY</h1>
            <div class="stats">{date_range} | {stats.total_videos} videos | {stats.days_covered} days | {len(stats.channels)} channels</div>
        </div>

        <div class="section one-thing">
            <div class="section-title">The One Thing</div>
            <h2>{content.the_one_thing.headline}</h2>
            <p>{content.the_one_thing.subtext}</p>
        </div>

        <div class="section quote">
            <div class="section-title">Quote of the Week</div>
            <div class="quote-text">"{content.quote_of_the_week.text}"</div>
            <div class="quote-author">-- {content.quote_of_the_week.speaker}</div>
        </div>

        <div class="section watch-one">
            <div class="section-title">Watch If You Only Watch One</div>
            <a href="{watch_url}" class="video-title">{watch.title}</a>
            <div class="video-meta">{watch.channel} | {watch.duration_minutes} min</div>
            <div class="why">Why: {watch.why}</div>
        </div>

        <div class="section">
            <div class="section-title">Numbers That Matter</div>
            {numbers_html}
        </div>

        <div class="section contrarian">
            <div class="section-title">Contrarian Take</div>
            <div class="label">They say:</div>
            <div class="conventional">{content.contrarian_take.conventional}</div>
            <div class="label">Actually:</div>
            <div class="actual">{content.contrarian_take.actual}</div>
        </div>

        <div class="section concept">
            <div class="section-title">Concept of the Week</div>
            <h3>{concept_title}</h3>
            <p>{concept.definition}</p>
        </div>

        <div class="section">
            <div class="section-title">{len(content.themes)} Themes This Week</div>
            {themes_html}
        </div>

        <div class="section">
            <div class="section-title">All Videos by Category</div>
            {categories_html}
        </div>

        <div class="section weekly-note">
            <div class="section-title">Weekly Note</div>
            <p>{content.weekly_note}</p>
        </div>

        <div class="footer">
            Generated with AI | Confidence: {content.confidence_score:.0%}
        </div>
    </div>
</body>
</html>"""

    return html
