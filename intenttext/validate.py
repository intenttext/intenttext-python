from __future__ import annotations

import re
from typing import Iterable

from .types import IntentDocument, ValidationIssue, ValidationResult


def validate(doc: IntentDocument) -> ValidationResult:
    issues: list[ValidationIssue] = []

    step_ids = {
        block.id
        for block in doc.blocks
        if block.type in {"step", "decision", "parallel", "gate", "call", "result", "handoff", "wait", "retry"}
    }
    all_ids = [block.id for block in doc.blocks]

    has_track = any(block.type == "track" for block in doc.blocks)
    has_sign = any(block.type == "sign" for block in doc.blocks)
    has_freeze = any(block.type == "freeze" for block in doc.blocks)

    # Duplicate block IDs
    seen: set[str] = set()
    for block_id in all_ids:
        if block_id in seen:
            issues.append(
                ValidationIssue(
                    block_id=block_id,
                    block_type="document",
                    type="error",
                    code="DUPLICATE_ID",
                    message=f"Duplicate block id '{block_id}'",
                )
            )
        seen.add(block_id)

    context_vars = set(doc.metadata.context.keys())
    produced_vars = {
        str(block.properties.get("output"))
        for block in doc.blocks
        if "output" in block.properties and str(block.properties.get("output"))
    }

    for block in doc.blocks:
        if block.type == "gate" and not block.properties.get("approver"):
            issues.append(
                ValidationIssue(
                    block_id=block.id,
                    block_type=block.type,
                    type="error",
                    code="GATE_APPROVER_REQUIRED",
                    message="gate: block requires approver property",
                )
            )

        depends = block.properties.get("depends")
        if isinstance(depends, str) and depends and depends not in step_ids:
            issues.append(
                ValidationIssue(
                    block_id=block.id,
                    block_type=block.type,
                    type="error",
                    code="STEP_REF_MISSING",
                    message=f"depends references missing step '{depends}'",
                )
            )

        if block.type == "decision":
            for key in ("then", "else"):
                ref = block.properties.get(key)
                if isinstance(ref, str) and ref and ref not in step_ids:
                    issues.append(
                        ValidationIssue(
                            block_id=block.id,
                            block_type=block.type,
                            type="error",
                            code="STEP_REF_MISSING",
                            message=f"decision {key} references missing step '{ref}'",
                        )
                    )

        if block.type == "parallel":
            steps = block.properties.get("steps")
            if isinstance(steps, str):
                for ref in [s.strip() for s in steps.split(",") if s.strip()]:
                    if ref not in step_ids:
                        issues.append(
                            ValidationIssue(
                                block_id=block.id,
                                block_type=block.type,
                                type="error",
                                code="STEP_REF_MISSING",
                                message=f"parallel steps references missing step '{ref}'",
                            )
                        )

        for var in _extract_vars(block):
            # runtime placeholders are intentionally unresolved
            if var in {"page", "pages"}:
                continue
            top = var.split(".")[0]
            if top not in context_vars and top not in produced_vars:
                issues.append(
                    ValidationIssue(
                        block_id=block.id,
                        block_type=block.type,
                        type="warning",
                        code="VARIABLE_UNRESOLVED",
                        message=f"Variable '{{{{{var}}}}}' is not declared in context: or step output",
                    )
                )

    # Trust validation: freeze without sign
    if has_freeze and not has_sign:
        issues.append(
            ValidationIssue(
                block_id="document",
                block_type="document",
                type="warning",
                code="FREEZE_WITHOUT_SIGN",
                message="Document is frozen but has no signatures",
            )
        )

    # Trust validation: sign/freeze without track
    if (has_sign or has_freeze) and not has_track:
        issues.append(
            ValidationIssue(
                block_id="document",
                block_type="document",
                type="warning",
                code="TRUST_WITHOUT_TRACK",
                message="Document has sign/freeze blocks but no track: block",
            )
        )

    has_errors = any(issue.type == "error" for issue in issues)
    return ValidationResult(valid=not has_errors, issues=issues)


def _extract_vars(block) -> Iterable[str]:
    pattern = re.compile(r"\{\{([^}]+)\}\}")
    values = [block.content, block.original_content]
    values.extend(str(v) for v in block.properties.values() if isinstance(v, str))

    for value in values:
        for match in pattern.finditer(value):
            yield match.group(1).strip()
