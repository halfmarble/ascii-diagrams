# Output format after terrylica/cc-skills plugins/doc-tools/skills/ascii-diagram-validator/scripts/check_ascii_alignment.py (MIT); see THIRD_PARTY_NOTICES.md
"""Text and JSON output for check results.

`results` is a list of (path, findings) pairs; a finding has line, col,
severity, rule, message, suggestion and to_dict().
"""
from __future__ import annotations

import json

SEVERITIES = ("error", "warning", "info")


def counts(results) -> dict:
    out = {s: 0 for s in SEVERITIES}
    for _, findings in results:
        for f in findings:
            out[f.severity] = out.get(f.severity, 0) + 1
    return out


def format_text(results) -> str:
    """`path:line:col: severity: [rule] message`, with an indented suggestion line."""
    lines = []
    for path, findings in results:
        for f in findings:
            lines.append("%s:%d:%d: %s: [%s] %s" % (path, f.line, f.col, f.severity, f.rule, f.message))
            if f.suggestion:
                lines.append("  suggestion: %s" % f.suggestion)
    return "\n".join(lines)


def summary(results) -> str:
    c = counts(results)
    return "%d errors, %d warnings, %d info in %d files" % (c["error"], c["warning"], c["info"], len(results))


def to_json_obj(results) -> dict:
    return {
        "version": 1,
        "files": [{"path": path, "findings": [f.to_dict() for f in findings]}
                  for path, findings in results],
        "counts": counts(results),
    }


def format_json(results, indent=2) -> str:
    return json.dumps(to_json_obj(results), indent=indent, ensure_ascii=False)
