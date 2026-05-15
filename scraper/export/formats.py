"""Export scraped data to various formats."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any


def to_json(data: dict[str, Any], filepath: str | None = None) -> str:
    content = json.dumps(data, indent=2, ensure_ascii=False)
    if filepath:
        Path(filepath).write_text(content, encoding="utf-8")
    return content


def to_csv(data: dict[str, Any], filepath: str | None = None) -> str:
    """Flatten scraped data into rows for CSV export."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["type", "key", "value"])

    # Metadata
    writer.writerow(["page", "url", data.get("url", "")])
    writer.writerow(["page", "title", data.get("title", "")])
    writer.writerow(["page", "description", data.get("description", "")])

    # Links
    for link in data.get("links", []):
        writer.writerow(["link", link.get("text", ""), link.get("href", "")])

    # Images
    for img in data.get("images", []):
        writer.writerow(["image", img.get("alt", ""), img.get("src", "")])

    # Emails
    for email in data.get("emails", []):
        writer.writerow(["email", email, ""])

    # Phones
    for phone in data.get("phones", []):
        writer.writerow(["phone", phone, ""])

    # Social links
    for sl in data.get("social_links", []):
        writer.writerow(["social", sl.get("text", ""), sl.get("href", "")])

    content = output.getvalue()
    if filepath:
        Path(filepath).write_text(content, encoding="utf-8")
    return content


def to_markdown(data: dict[str, Any], filepath: str | None = None) -> str:
    """Convert scraped data to readable markdown."""
    lines: list[str] = []
    lines.append(f"# {data.get('title', 'Untitled')}")
    lines.append(f"> {data.get('description', '')}")
    lines.append(f"> URL: {data.get('url', '')}")
    lines.append("")

    if data.get("emails"):
        lines.append("## Emails")
        for e in data["emails"]:
            lines.append(f"- {e}")
        lines.append("")

    if data.get("phones"):
        lines.append("## Phone Numbers")
        for p in data["phones"]:
            lines.append(f"- {p}")
        lines.append("")

    if data.get("social_links"):
        lines.append("## Social Links")
        for s in data["social_links"]:
            lines.append(f"- [{s.get('text', s['href'])}]({s['href']})")
        lines.append("")

    if data.get("images"):
        lines.append("## Images")
        for img in data["images"]:
            lines.append(f"- {img.get('alt', 'No alt')} - {img['src']}")
        lines.append("")

    if data.get("tables"):
        for i, table in enumerate(data["tables"]):
            lines.append(f"## Table {i + 1}")
            headers = table.get("headers", [])
            if headers:
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for row in table.get("rows", []):
                if isinstance(row, dict):
                    vals = [str(row.get(h, "")) for h in headers]
                else:
                    vals = [str(v) for v in row.get("cells", [])]
                lines.append("| " + " | ".join(vals) + " |")
            lines.append("")

    if data.get("text_content"):
        text = data["text_content"][:5000]
        lines.append("## Page Content")
        lines.append(text)
        if len(data["text_content"]) > 5000:
            lines.append(f"\n... (truncated, {len(data['text_content'])} chars total)")

    content = "\n".join(lines)
    if filepath:
        Path(filepath).write_text(content, encoding="utf-8")
    return content


def to_html(data: dict[str, Any], filepath: str | None = None) -> str:
    """Convert scraped data to a standalone HTML report."""
    template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scrape Report - {title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 960px; margin: 0 auto; padding: 2rem; background: #0d1117; color: #c9d1d9; }}
h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 0.5rem; }}
h2 {{ color: #79c0ff; margin-top: 2rem; }}
a {{ color: #58a6ff; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #30363d; padding: 0.5rem; text-align: left; }}
th {{ background: #161b22; color: #79c0ff; }}
tr:nth-child(even) {{ background: #161b22; }}
.meta {{ color: #8b949e; font-size: 0.9rem; }}
.section {{ background: #161b22; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
.email::before {{ content: "📧 "; }}
.phone::before {{ content: "📞 "; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="meta">{description}<br><strong>URL:</strong> <a href="{url}">{url}</a> | <strong>Status:</strong> {status}</p>

<h2>📧 Emails ({email_count})</h2>
<div class="section">
{emails_html}
</div>

<h2>📞 Phones ({phone_count})</h2>
<div class="section">
{phones_html}
</div>

<h2>🔗 Social Links ({social_count})</h2>
<div class="section">
{social_html}
</div>

<h2>🖼️ Images ({image_count})</h2>
<div class="section">
{images_html}
</div>

<h2>📊 Tables ({table_count})</h2>
{tables_html}

<h2>📝 Page Content</h2>
<div class="section" style="white-space: pre-wrap; max-height: 600px; overflow-y: auto;">{text_content}</div>

</body>
</html>"""

    html = template.format(
        title=data.get("title", "Untitled"),
        description=data.get("description", ""),
        url=data.get("url", ""),
        status=data.get("status_code", ""),
        email_count=len(data.get("emails", [])),
        phone_count=len(data.get("phones", [])),
        social_count=len(data.get("social_links", [])),
        image_count=len(data.get("images", [])),
        table_count=len(data.get("tables", [])),
        emails_html="<br>".join(f'<span class="email">{e}</span>' for e in data.get("emails", [])) or "<em>None found</em>",
        phones_html="<br>".join(f'<span class="phone">{p}</span>' for p in data.get("phones", [])) or "<em>None found</em>",
        social_html="<br>".join(f'<a href="{s["href"]}" target="_blank">{s.get("text", s["href"])}</a>' for s in data.get("social_links", [])) or "<em>None found</em>",
        images_html="<br>".join(f'<a href="{i["src"]}" target="_blank">{i.get("alt", "Image")}</a>' for i in data.get("images", [])) or "<em>None found</em>",
        tables_html=_tables_to_html(data.get("tables", [])),
        text_content=data.get("text_content", "")[:10000],
    )

    if filepath:
        Path(filepath).write_text(html, encoding="utf-8")
    return html


def _tables_to_html(tables: list[dict]) -> str:
    parts: list[str] = []
    for table in tables:
        headers = table.get("headers", [])
        rows = table.get("rows", [])
        html = '<table><thead><tr>'
        for h in headers:
            html += f"<th>{h}</th>"
        html += "</tr></thead><tbody>"
        for row in rows:
            html += "<tr>"
            if isinstance(row, dict):
                for h in headers:
                    html += f"<td>{row.get(h, '')}</td>"
            else:
                for cell in row.get("cells", []):
                    html += f"<td>{cell}</td>"
            html += "</tr>"
        html += "</tbody></table>"
        parts.append(html)
    return "<br>".join(parts)
