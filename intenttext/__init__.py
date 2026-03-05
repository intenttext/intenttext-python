from .merge import merge_data, parse_and_merge
from .parser import parse, parse_safe
from .query import query
from .renderer import render_html, render_markdown, render_print
from .source import to_source
from .types import (
    InlineSegment,
    IntentBlock,
    IntentDocument,
    IntentMetadata,
    ParseResult,
    ParseWarning,
    ValidationIssue,
    ValidationResult,
)
from .validate import validate

__version__ = "1.0.0"

__all__ = [
    "parse",
    "parse_safe",
    "render_html",
    "render_print",
    "render_markdown",
    "merge_data",
    "parse_and_merge",
    "validate",
    "query",
    "to_source",
    "IntentDocument",
    "IntentBlock",
    "IntentMetadata",
    "InlineSegment",
    "ParseResult",
    "ParseWarning",
    "ValidationResult",
    "ValidationIssue",
]
