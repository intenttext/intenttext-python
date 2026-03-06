from __future__ import annotations

import re
from typing import Any, Optional

from .types import (
    InlineSegment,
    IntentBlock,
    IntentDocument,
    IntentMetadata,
    ParseResult,
    ParseWarning,
)

DOCUMENT_HEADER_KEYWORDS = {
    "agent",
    "context",
    "font",
    "page",
}

STRUCTURE_KEYWORDS = {
    "title",
    "summary",
    "section",
    "sub",
    "note",
    "toc",
    "break",
}

CONTENT_KEYWORDS = {
    "task",
    "done",
    "ask",
    "quote",
    "info",
    "warning",
    "tip",
    "success",
    "link",
    "image",
    "code",
    "ref",
}

WRITER_KEYWORDS = {
    "byline",
    "epigraph",
    "caption",
    "footnote",
    "dedication",
}

AGENTIC_KEYWORDS = {
    "step",
    "decision",
    "parallel",
    "loop",
    "call",
    "gate",
    "wait",
    "retry",
    "error",
    "trigger",
    "checkpoint",
    "handoff",
    "audit",
    "emit",
    "result",
    "progress",
    "import",
    "export",
    "policy",
}

ALL_KEYWORDS = (
    DOCUMENT_HEADER_KEYWORDS
    | STRUCTURE_KEYWORDS
    | CONTENT_KEYWORDS
    | WRITER_KEYWORDS
    | AGENTIC_KEYWORDS
)

_ID_COUNTER = 0


def parse(source: str) -> IntentDocument:
    result = parse_safe(source)
    if result.errors:
        raise ValueError(f"Parse errors: {result.errors[0].message}")
    return result.document


def parse_safe(
    source: str,
    unknown_keyword: str = "note",
    max_blocks: int = 10000,
    max_line_length: int = 50000,
) -> ParseResult:
    warnings: list[ParseWarning] = []
    errors: list[ParseWarning] = []
    blocks: list[IntentBlock] = []
    metadata = IntentMetadata()
    in_code_fence = False
    fence_lines: list[str] = []

    lines = source.splitlines()

    for line_num, raw_line in enumerate(lines, 1):
        original = raw_line
        if len(raw_line) > max_line_length:
            raw_line = raw_line[:max_line_length]
            warnings.append(
                ParseWarning(
                    line=line_num,
                    message=f"Line truncated at {max_line_length} characters",
                    code="LINE_TRUNCATED",
                    original=original[:100] + "...",
                )
            )

        line = raw_line.strip()

        if line.startswith("```"):
            if in_code_fence:
                blocks.append(
                    IntentBlock(
                        id=_generate_id(),
                        type="code",
                        content="\n".join(fence_lines),
                        original_content="\n".join(fence_lines),
                    )
                )
                in_code_fence = False
                fence_lines = []
            else:
                in_code_fence = True
            continue

        if in_code_fence:
            fence_lines.append(raw_line)
            continue

        if not line:
            continue

        if line.startswith("//"):
            continue

        if line == "---":
            blocks.append(
                IntentBlock(
                    id=_generate_id(),
                    type="divider",
                    content="",
                    original_content="---",
                )
            )
            continue

        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line[1:-1].split("|")]
            if all(re.match(r"^[-:]+$", c.strip()) for c in cells if c.strip()):
                continue
            if blocks and blocks[-1].type == "table":
                rows = blocks[-1].properties.get("rows", [])
                rows.append(cells)
                blocks[-1].properties["rows"] = rows
            else:
                blocks.append(
                    IntentBlock(
                        id=_generate_id(),
                        type="table",
                        content="",
                        original_content=line,
                        properties={"rows": [cells]},
                    )
                )
            continue

        if len(blocks) >= max_blocks:
            warnings.append(
                ParseWarning(
                    line=line_num,
                    message=f"Max blocks ({max_blocks}) reached, stopping parse",
                    code="MAX_BLOCKS_REACHED",
                    original=line,
                )
            )
            break

        block = _parse_keyword_line(
            line=line,
            line_num=line_num,
            unknown_keyword=unknown_keyword,
            warnings=warnings,
            errors=errors,
        )
        if block is not None:
            blocks.append(block)
            _update_metadata(metadata, block)

    if in_code_fence:
        warnings.append(
            ParseWarning(
                line=len(lines),
                message="Unclosed code fence, auto-closed at end of file",
                code="UNCLOSED_CODE_FENCE",
                original="```",
            )
        )
        blocks.append(
            IntentBlock(
                id=_generate_id(),
                type="code",
                content="\n".join(fence_lines),
                original_content="\n".join(fence_lines),
            )
        )

    document = IntentDocument(version="2.0", blocks=blocks, metadata=metadata)
    return ParseResult(document=document, warnings=warnings, errors=errors)


def _parse_keyword_line(
    line: str,
    line_num: int,
    unknown_keyword: str,
    warnings: list[ParseWarning],
    errors: list[ParseWarning],
) -> Optional[IntentBlock]:
    match = re.match(r"^(\w+):\s*(.*)$", line)
    if not match:
        return None

    keyword = match.group(1).lower()
    rest = match.group(2)

    if keyword not in ALL_KEYWORDS:
        if unknown_keyword == "skip":
            warnings.append(
                ParseWarning(
                    line=line_num,
                    message=f"Unknown keyword '{keyword}' skipped",
                    code="UNKNOWN_KEYWORD",
                    original=line,
                )
            )
            return None
        if unknown_keyword == "throw":
            errors.append(
                ParseWarning(
                    line=line_num,
                    message=f"Unknown keyword '{keyword}'",
                    code="UNKNOWN_KEYWORD",
                    original=line,
                )
            )
            return None

        warnings.append(
            ParseWarning(
                line=line_num,
                message=f"Unknown keyword '{keyword}' treated as note",
                code="UNKNOWN_KEYWORD",
                original=line,
            )
        )
        keyword = "note"

    content, properties = _parse_content_and_properties(rest)

    if keyword == "done":
        keyword = "task"
        properties["status"] = "done"

    block_id = str(properties.pop("id", _generate_id()))

    return IntentBlock(
        id=block_id,
        type=keyword,
        content=_strip_inline(content),
        original_content=content,
        inline=_parse_inline(content),
        properties=properties,
    )


def _parse_content_and_properties(rest: str) -> tuple[str, dict[str, Any]]:
    parts = [p.strip() for p in rest.split("|")]
    content = parts[0].strip() if parts else ""
    properties: dict[str, Any] = {}

    for part in parts[1:]:
        kv_match = re.match(r"^(\w[\w-]*):\s*(.*)$", part.strip())
        if not kv_match:
            continue
        key = kv_match.group(1)
        value: Any = kv_match.group(2).strip()

        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        elif key in ("max", "delay", "leading", "depth", "columns"):
            try:
                value = int(value) if "." not in value else float(value)
            except ValueError:
                pass

        properties[key] = value

    return content, properties


def _parse_inline(text: str) -> list[InlineSegment]:
    segments: list[InlineSegment] = []
    pattern = re.compile(
        r"\*([^*]+)\*"
        r"|_([^_]+)_"
        r"|~([^~]+)~"
        r"|\^([^^]+)\^"
        r"|`([^`]+)`"
        r"|\[([^\]]+)\]\(([^)]+)\)"
        r"|\[\^(\d+)\]"
        r"|@(\w+)"
        r"|#(\w+)"
    )

    last_end = 0
    for match in pattern.finditer(text):
        if match.start() > last_end:
            segments.append(InlineSegment(type="text", value=text[last_end : match.start()]))

        if match.group(1):
            segments.append(InlineSegment(type="bold", value=match.group(1)))
        elif match.group(2):
            segments.append(InlineSegment(type="italic", value=match.group(2)))
        elif match.group(3):
            segments.append(InlineSegment(type="strikethrough", value=match.group(3)))
        elif match.group(4):
            segments.append(InlineSegment(type="highlight", value=match.group(4)))
        elif match.group(5):
            segments.append(InlineSegment(type="code", value=match.group(5)))
        elif match.group(6):
            segments.append(
                InlineSegment(type="link", value=match.group(6), href=match.group(7))
            )
        elif match.group(8):
            segments.append(InlineSegment(type="footnote-ref", value=match.group(8)))
        elif match.group(9):
            segments.append(InlineSegment(type="mention", value=match.group(9)))
        elif match.group(10):
            segments.append(InlineSegment(type="tag", value=match.group(10)))

        last_end = match.end()

    if last_end < len(text):
        segments.append(InlineSegment(type="text", value=text[last_end:]))

    return segments


def _strip_inline(text: str) -> str:
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"~([^~]+)~", r"\1", text)
    text = re.sub(r"\^([^^]+)\^", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[\^(\d+)\]", r"[\1]", text)
    return text


def _generate_id() -> str:
    global _ID_COUNTER
    _ID_COUNTER += 1
    return f"b{_ID_COUNTER:04d}"


def _update_metadata(metadata: IntentMetadata, block: IntentBlock) -> None:
    if block.type == "title":
        metadata.title = block.content
    elif block.type == "summary":
        metadata.summary = block.content
    elif block.type == "agent":
        metadata.agent = block.content
        if "model" in block.properties:
            metadata.model = str(block.properties["model"])
    elif block.type == "context":
        metadata.context.update({k: str(v) for k, v in block.properties.items()})
