# Ported from kouko/monkey-skills ascii-graph-toolkit/skills/ascii-graph/scripts/gen_flow.py (MIT); see THIRD_PARTY_NOTICES.md
"""Linear flow: labelled boxes stacked on one trunk, joined by a down arrow."""
from __future__ import annotations

from ..width import display_width, split_lines
from ._box import arrows, as_text, box, get_set


def render_flow(steps: "list[str]", style: str = "light") -> str:
    st = get_set(style)
    head = arrows(style)["down"]
    if not steps:
        return ""
    for s in steps:
        as_text(s, "flow step")
    interior = max(display_width(l) for s in steps for l in split_lines(s)) + 2
    trunk = " " * (1 + interior // 2)
    lines = []  # type: list[str]
    for i, step in enumerate(steps):
        rows = box(split_lines(step), interior, st)
        if i != len(steps) - 1:
            # the trunk leaves through a junction drawn into the bottom border
            c = len(trunk)
            rows[-1] = rows[-1][:c] + st["tee_d"] + rows[-1][c + 1:]
        lines.extend(rows)
        if i != len(steps) - 1:
            lines.append(trunk + st["v"])
            lines.append(trunk + head)
    return "\n".join(lines)
