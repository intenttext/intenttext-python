# IntentText Python

Python implementation of the IntentText parser and renderer.

Independent implementation (not a Node.js wrapper), designed for Python workflows and AI stacks.

## Install

```bash
pip install intenttext
```

## Quick Start

```python
from intenttext import parse, render_html, merge_data, validate, query

# Parse a document
source = """
title: Sprint Planning
section: Tasks
task: Write tests | owner: Ahmed | due: Friday
task: Deploy to staging | owner: Sarah | due: Monday
gate: Final approval | approver: Lead | timeout: 24h
""".strip()

doc = parse(source)

# Query for tasks
tasks = query(doc, type="task")
for task in tasks:
    print(f"{task.content} -> {task.properties.get('owner', 'unassigned')}")

# Validate workflow semantics
result = validate(doc)
if not result.valid:
    for issue in result.issues:
        print(f"[{issue.type.upper()}] {issue.message}")

# Render to HTML
html = render_html(doc)
```

## API

- `parse(source: str) -> IntentDocument`
- `parse_safe(source: str, ...) -> ParseResult`
- `render_html(doc: IntentDocument, include_css: bool = True) -> str`
- `render_print(doc: IntentDocument) -> str`
- `render_markdown(doc: IntentDocument) -> str`
- `merge_data(template: IntentDocument, data: dict) -> IntentDocument`
- `parse_and_merge(template_source: str, data: dict) -> IntentDocument`
- `validate(doc: IntentDocument) -> ValidationResult`
- `query(doc: IntentDocument, ...) -> list[IntentBlock]`
- `to_source(doc: IntentDocument) -> str`

## Development

```bash
pip install -e .[dev]
pytest
```

## License

MIT
