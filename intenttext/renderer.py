from __future__ import annotations

import html

from .types import IntentBlock, IntentDocument


BASE_CSS = """
.it-document { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #222; }
.it-block { margin: 0.6rem 0; }
.it-section { margin-top: 1.4rem; }
.it-sub { margin-top: 1rem; }
.it-callout { padding: 0.75rem 1rem; border-radius: 6px; border-left: 4px solid; }
.it-callout.info { background: #eef6ff; border-color: #1d70b8; }
.it-callout.warning { background: #fff7e6; border-color: #b26a00; }
.it-callout.tip { background: #eefbf2; border-color: #1f7a3d; }
.it-callout.success { background: #eefbf2; border-color: #1f7a3d; }
.it-task { display: flex; gap: 0.5rem; }
.it-task.done { color: #666; text-decoration: line-through; }
.it-table { width: 100%; border-collapse: collapse; }
.it-table th, .it-table td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }
.it-table th { background: #f5f5f5; }
.it-divider { border: 0; border-top: 1px solid #ddd; margin: 1rem 0; }
""".strip()


def render_html(doc: IntentDocument, include_css: bool = True) -> str:
    parts: list[str] = []
    if include_css:
        parts.append(f"<style>{BASE_CSS}</style>")

    parts.append('<div class="it-document">')
    for block in doc.blocks:
        parts.append(_render_block_html(block))
    parts.append("</div>")

    return "\n".join(p for p in parts if p)


def render_print(doc: IntentDocument) -> str:
    css = (
        BASE_CSS
        + "\n@media print { .it-document { font-family: Georgia, serif; } .it-block { break-inside: avoid; } }"
    )
    body = render_html(doc, include_css=False)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"/>"
        f"<style>{css}</style></head><body>{body}</body></html>"
    )


def render_markdown(doc: IntentDocument) -> str:
    lines: list[str] = []

    for block in doc.blocks:
        t = block.type
        content = block.original_content or block.content

        if t == "title":
            lines.append(f"# {content}")
        elif t == "section":
            lines.append(f"## {content}")
        elif t == "sub":
            lines.append(f"### {content}")
        elif t == "note":
            lines.append(content)
        elif t == "task":
            checked = str(block.properties.get("status", "")).lower() == "done"
            lines.append(f"- [{'x' if checked else ' '}] {content}")
        elif t == "quote":
            author = block.properties.get("by")
            lines.append(f"> {content}")
            if author:
                lines.append(f"> - {author}")
        elif t in {"info", "warning", "tip"}:
            lines.append(f"> **{t.upper()}:** {content}")
        elif t == "table":
            rows = block.properties.get("rows", [])
            if rows:
                header = rows[0]
                lines.append("| " + " | ".join(str(v) for v in header) + " |")
                lines.append("| " + " | ".join("---" for _ in header) + " |")
                for row in rows[1:]:
                    lines.append("| " + " | ".join(str(v) for v in row) + " |")
        elif t == "divider":
            lines.append("---")
        else:
            lines.append(f"{content}")

        if lines and lines[-1] != "":
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def _render_block_html(block: IntentBlock) -> str:
    t = block.type
    content = html.escape(block.content)

    if t == "title":
        return f'<h1 class="it-block it-title">{content}</h1>'
    if t == "summary":
        return f'<p class="it-block it-summary">{content}</p>'
    if t == "section":
        return f'<h2 class="it-block it-section">{content}</h2>'
    if t == "sub":
        return f'<h3 class="it-block it-sub">{content}</h3>'
    if t == "quote":
        by = block.properties.get("by")
        footer = f"<cite>{html.escape(str(by))}</cite>" if by else ""
        return f'<blockquote class="it-block it-quote"><p>{content}</p>{footer}</blockquote>'
    if t in {"note", "info", "warning", "tip", "success"}:
        extra = "it-callout " + (t if t != "note" else "info")
        return f'<div class="it-block {extra}"><span class="it-keyword">{t}:</span> {content}</div>'
    if t == "task":
        done = str(block.properties.get("status", "")).lower() == "done"
        mark = "[x]" if done else "[ ]"
        done_cls = " done" if done else ""
        return f'<div class="it-block it-task{done_cls}"><span>{mark}</span><span>{content}</span></div>'
    if t == "image":
        src = html.escape(str(block.properties.get("src", "")))
        alt = html.escape(str(block.properties.get("alt", block.content)))
        return f'<figure class="it-block it-image"><img src="{src}" alt="{alt}"/></figure>'
    if t == "link":
        href = html.escape(str(block.properties.get("href", "#")))
        return f'<p class="it-block it-link"><a href="{href}">{content}</a></p>'
    if t == "code":
        return f'<pre class="it-block it-code"><code>{content}</code></pre>'
    if t == "table":
        rows = block.properties.get("rows", [])
        if not rows:
            return ""
        header = rows[0]
        body_rows = rows[1:]
        thead = "".join(f"<th>{html.escape(str(c))}</th>" for c in header)
        tbody = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>"
            for row in body_rows
        )
        return f'<table class="it-block it-table"><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>'
    if t == "divider":
        return '<hr class="it-block it-divider"/>'

    return f'<p class="it-block it-{html.escape(t)}">{content}</p>'
