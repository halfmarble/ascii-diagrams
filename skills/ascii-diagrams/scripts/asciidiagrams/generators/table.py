# Ported from kouko/monkey-skills ascii-graph-toolkit/skills/ascii-graph/scripts/gen_table.py (MIT); see THIRD_PARTY_NOTICES.md
"""Display-width aligned table generator.

Column widths and cell padding use display cells, so wide (CJK) cells align.
"""
from __future__ import annotations

from ..width import display_width, split_lines
from ._box import as_text, get_set, pad


def render_table(headers: "list[str]", rows: "list[list[str]]", style: str = "light") -> str:
    st = get_set(style)
    if not headers:
        return ""
    for r in rows:
        if len(r) != len(headers):
            raise ValueError("row has %d cells, expected %d: %r" % (len(r), len(headers), r))
    all_rows = [list(headers)] + [list(r) for r in rows]
    for row in all_rows:
        for c in row:
            as_text(c, "table cell")
    col_widths = [
        max(display_width(line) for row in all_rows for line in split_lines(row[i]))
        for i in range(len(headers))
    ]

    def border(left: str, mid: str, right: str) -> str:
        return left + mid.join(st["h"] * (w + 2) for w in col_widths) + right

    def data_lines(cells: "list[str]") -> "list[str]":
        split = [split_lines(c) for c in cells]
        height = max(len(s) for s in split)
        out = []
        for i in range(height):
            parts = [" " + pad(s[i] if i < len(s) else "", col_widths[k]) + " "
                     for k, s in enumerate(split)]
            out.append(st["v"] + st["v"].join(parts) + st["v"])
        return out

    lines = [border(st["tl"], st["tee_d"], st["tr"])]
    lines += data_lines(all_rows[0])
    lines.append(border(st["tee_r"], st["cross"], st["tee_l"]))
    for row in all_rows[1:]:
        lines += data_lines(row)
    lines.append(border(st["bl"], st["tee_u"], st["br"]))
    return "\n".join(lines)
