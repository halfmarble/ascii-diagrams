# Ported from kouko/monkey-skills ascii-graph-toolkit/skills/ascii-graph/scripts/gen_bar.py (MIT); see THIRD_PARTY_NOTICES.md
"""Horizontal bar chart with display-width aligned labels."""
from __future__ import annotations

from ..width import display_width
from ._box import as_text, bar_fill, pad, single_line


def render_bar(pairs: "list[tuple[str, float]]", width: int = 20, style: str = "light") -> str:
    fill = bar_fill(style)
    if not pairs:
        return ""
    if not isinstance(width, int) or isinstance(width, bool) or width < 1:
        raise ValueError("bar width must be a positive integer, got %r" % (width,))
    for label, value in pairs:
        single_line(as_text(label, "bar label"), "bar label")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError("bar value must be a number >= 0, got %r" % (value,))
    label_width = max(display_width(l) for l, _ in pairs)
    max_value = max(v for _, v in pairs)
    lines = []
    for label, value in pairs:
        n = int(round(value / max_value * width)) if max_value else 0
        lines.append("%s %s %s" % (pad(label, label_width), fill * n, value))
    return "\n".join(lines)
