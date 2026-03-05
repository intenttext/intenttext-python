from __future__ import annotations

from typing import Any, Optional

from .types import IntentBlock, IntentDocument


def query(
    doc: IntentDocument,
    type: Optional[str | list[str]] = None,
    section: Optional[str] = None,
    properties: Optional[dict[str, Any]] = None,
    text: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[IntentBlock]:
    results: list[IntentBlock] = []
    current_section = ""

    for block in doc.blocks:
        if block.type == "section":
            current_section = block.content

        if type is not None:
            if isinstance(type, str) and block.type != type:
                continue
            if isinstance(type, list) and block.type not in type:
                continue

        if section is not None and current_section != section:
            continue

        if text is not None and text.lower() not in block.content.lower():
            continue

        if properties:
            matches = True
            for key, expected in properties.items():
                actual = block.properties.get(key)
                if callable(getattr(expected, "search", None)):
                    if actual is None or expected.search(str(actual)) is None:
                        matches = False
                        break
                else:
                    if str(actual) != str(expected):
                        matches = False
                        break
            if not matches:
                continue

        results.append(block)

        if limit is not None and len(results) >= limit:
            break

    return results
