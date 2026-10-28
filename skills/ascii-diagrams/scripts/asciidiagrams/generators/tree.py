# Ported from kouko/monkey-skills ascii-graph-toolkit/skills/ascii-graph/scripts/gen_tree.py (MIT); see THIRD_PARTY_NOTICES.md
"""Tree / hierarchy renderer. A node is {"label": str, "children": [node, ...]}."""
from __future__ import annotations

from ..width import split_lines
from ._box import as_text, get_set


def render_tree(node: dict, style: str = "light") -> str:
    st = get_set(style)
    tee = st["tee_r"] + st["h"] + " "
    elbow = st["bl"] + st["h"] + " "
    if style == "ascii":
        elbow = "`- "
        tee = "|- "
    bar = st["v"] + "  "
    gap = "   "
    if not isinstance(node, dict) or "label" not in node:
        raise ValueError("tree node needs a label: %r" % (node,))
    lines = list(split_lines(as_text(node["label"], "tree label")))

    def walk(children: list, prefix: str) -> None:
        last = len(children) - 1
        for i, child in enumerate(children):
            if not isinstance(child, dict) or "label" not in child:
                raise ValueError("tree node needs a label: %r" % (child,))
            is_last = i == last
            label_lines = split_lines(as_text(child["label"], "tree label"))
            lines.append(prefix + (elbow if is_last else tee) + label_lines[0])
            cont = gap if is_last else bar
            for extra in label_lines[1:]:
                lines.append(prefix + cont + extra)
            walk(child.get("children") or [], prefix + cont)

    walk(node.get("children") or [], "")
    return "\n".join(lines)
