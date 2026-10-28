# Ported from kouko/monkey-skills ascii-graph-toolkit/skills/ascii-graph/scripts/gen_arch.py (MIT); see THIRD_PARTY_NOTICES.md
"""Layered architecture: one box per layer, a name row, then component cells."""
from __future__ import annotations

from ..width import display_width, split_lines
from ._box import as_text, center, get_set


def _cell_width(label: str) -> int:
    return max(display_width(l) for l in split_lines(label)) + 2


def _natural(components: "list[str]") -> int:
    return sum(_cell_width(c) for c in components) + max(len(components) - 1, 0)


def render_arch(layers: "list[dict]", style: str = "light") -> str:
    st = get_set(style)
    if not layers:
        return ""
    for layer in layers:
        if not isinstance(layer, dict) or "name" not in layer or "components" not in layer:
            raise ValueError("arch layer needs name and components: %r" % (layer,))
        as_text(layer["name"], "layer name")
        for c in layer["components"]:
            as_text(c, "component")

    def name_width(name: str) -> int:
        return max(display_width(l) for l in split_lines(name))

    interior = max(max(_natural(l["components"]), name_width(l["name"])) for l in layers)
    lines = []  # type: list[str]
    for layer in layers:
        comps = layer["components"] or [""]
        n = len(comps)
        slack = interior - _natural(comps)
        base, rem = divmod(slack, n)
        widths = [_cell_width(c) + base + (1 if i >= n - rem else 0) for i, c in enumerate(comps)]
        height = max(len(split_lines(c)) for c in comps)
        grids = []
        for c, w in zip(comps, widths):
            phys = [" " + l + " " * (w - display_width(l) - 1) for l in split_lines(c)]
            phys += [" " * w] * (height - len(phys))
            grids.append(phys)
        seams = []
        col = 0
        for w in widths[:-1]:
            col += w
            seams.append(col)
            col += 1

        def border(left: str, junction: str, right: str) -> str:
            chars = [st["h"]] * interior
            for sc in seams:
                chars[sc] = junction
            return left + "".join(chars) + right

        lines.append(st["tl"] + st["h"] * interior + st["tr"])
        for nl in split_lines(layer["name"]):
            lines.append(st["v"] + center(nl, interior) + st["v"])
        lines.append(border(st["tee_r"], st["tee_d"], st["tee_l"]))
        for r in range(height):
            lines.append(st["v"] + st["v"].join(g[r] for g in grids) + st["v"])
        lines.append(border(st["bl"], st["tee_u"], st["br"]))
    return "\n".join(lines)
