"""IntentText Document Trust — hash, seal, verify, history boundary."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional


def find_history_boundary(source: str) -> int:
    """Find position of the history boundary in source. Returns -1 if not found."""
    lines = source.split("\n")
    pos = 0
    for i in range(len(lines) - 1):
        stripped = lines[i].strip()
        if stripped == "---":
            next_stripped = lines[i + 1].strip()
            if next_stripped == "// history" or next_stripped.startswith(
                "// history"
            ):
                return pos
        pos += len(lines[i]) + 1
    return -1


def compute_document_hash(source: str) -> str:
    """Compute SHA-256 hash of document content above history boundary,
    excluding sign: and freeze: lines."""
    boundary = find_history_boundary(source)
    content = source[:boundary] if boundary != -1 else source
    # Strip sign: and freeze: lines (their hashes reference the body without them)
    body_lines = [
        line
        for line in content.split("\n")
        if not line.startswith("sign:") and not line.startswith("freeze:")
    ]
    body = "\n".join(body_lines).strip()
    hash_hex = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"sha256:{hash_hex}"


def _parse_props(text: str) -> dict:
    """Parse pipe-delimited properties from a line like 'key: value | k2: v2'."""
    props: dict = {}
    for segment in text.split("|"):
        segment = segment.strip()
        colon = segment.find(":")
        if colon != -1:
            props[segment[:colon].strip()] = segment[colon + 1 :].strip()
    return props


def verify_document(source: str) -> dict:
    """Verify integrity of a sealed IntentText document.

    Returns:
        dict with keys: intact, frozen, frozen_at, signers, hash, expected_hash, error
    """
    boundary = find_history_boundary(source)
    content = source[:boundary] if boundary != -1 else source
    lines = content.split("\n")

    freeze_props: Optional[dict] = None
    sign_entries: list[dict] = []

    for line in lines:
        if line.startswith("freeze:"):
            freeze_props = _parse_props(line[len("freeze:") :])
        elif line.startswith("sign:"):
            rest = line[len("sign:") :].strip()
            # First segment before | is the signer name
            parts = rest.split("|")
            signer = parts[0].strip()
            props = _parse_props("|".join(parts[1:]))
            props["signer"] = signer
            sign_entries.append(props)

    if not freeze_props:
        return {
            "intact": False,
            "frozen": False,
            "warning": "Document is not sealed. No freeze: block found.",
        }

    current_hash = compute_document_hash(source)
    expected_hash = freeze_props.get("hash", "")
    intact = current_hash == expected_hash

    signers = [
        {
            "signer": s.get("signer"),
            "role": s.get("role"),
            "at": s.get("at"),
            "valid": s.get("hash") == current_hash,
        }
        for s in sign_entries
    ]

    return {
        "intact": intact,
        "frozen": True,
        "frozen_at": freeze_props.get("at"),
        "signers": signers,
        "hash": current_hash,
        "expected_hash": expected_hash,
        "error": None if intact else "Document has been modified since sealing.",
    }


def seal_document(
    source: str,
    signer: str,
    role: Optional[str] = None,
    skip_sign: bool = False,
) -> dict:
    """Seal a document with a signature and freeze block.

    Returns:
        dict with keys: success, hash, source, at
    """
    hash_val = compute_document_hash(source)
    at = datetime.now(timezone.utc).isoformat()

    boundary = find_history_boundary(source)
    insert_before = boundary if boundary != -1 else len(source)

    before = source[:insert_before]
    after = source[insert_before:]

    sign_line = (
        ""
        if skip_sign
        else f"sign: {signer}{f' | role: {role}' if role else ''} | at: {at} | hash: {hash_val}\n"
    )
    freeze_line = f"freeze: | at: {at} | hash: {hash_val} | status: locked\n"

    needs_newline = before and not before.endswith("\n")
    updated = before + ("\n" if needs_newline else "") + sign_line + freeze_line + after

    return {"success": True, "hash": hash_val, "source": updated, "at": at}
