from __future__ import annotations

from .types import IntentDocument


def to_source(doc: IntentDocument) -> str:
    lines: list[str] = []

    for block in doc.blocks:
        if block.type == "divider":
            lines.append("---")
            continue

        if block.type == "table":
            for row in block.properties.get("rows", []):
                lines.append("| " + " | ".join(str(c) for c in row) + " |")
            continue

        keyword = block.type
        props = dict(block.properties)

        if block.type == "task" and str(props.get("status", "")).lower() == "done":
            keyword = "done"
            props.pop("status", None)

        parts = [f"{keyword}: {block.original_content or block.content}".rstrip()]
        for key, value in props.items():
            parts.append(f"{key}: {value}")

        lines.append(" | ".join(parts))

    return "\n".join(lines)
