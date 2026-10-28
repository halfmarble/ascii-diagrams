"""Generators: table, flow, tree, bar, arch, seq, each in five styles."""
from __future__ import annotations

from ._box import STYLES
from .arch import render_arch
from .bar import render_bar
from .flow import render_flow
from .seq import render_seq
from .table import render_table
from .tree import render_tree

SHAPES = ("table", "flow", "tree", "bar", "arch", "seq")


def _need(payload: dict, key: str) -> object:
    if not isinstance(payload, dict) or key not in payload:
        raise ValueError("payload needs %r" % key)
    return payload[key]


def render(shape: str, payload: dict) -> str:
    """Render one shape from a JSON-style payload.

    The payload may carry "style" (light heavy double rounded ascii, default
    light). For tables the older "ascii_only": true means style "ascii".
    ValueError for an unknown shape, style or malformed payload.
    """
    if shape not in SHAPES:
        raise ValueError("unknown shape: %r (expected one of %s)" % (shape, ", ".join(SHAPES)))
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    style = payload.get("style", "light")
    if shape == "table" and payload.get("ascii_only") and "style" not in payload:
        style = "ascii"
    if shape == "table":
        return render_table(_need(payload, "headers"), _need(payload, "rows"), style=style)
    if shape == "flow":
        return render_flow(_need(payload, "steps"), style=style)
    if shape == "tree":
        return render_tree(_need(payload, "node"), style=style)
    if shape == "bar":
        pairs = [(p[0], p[1]) for p in _need(payload, "pairs")]
        return render_bar(pairs, width=payload.get("width", 20), style=style)
    if shape == "arch":
        return render_arch(_need(payload, "layers"), style=style)
    return render_seq(_need(payload, "participants"), _need(payload, "messages"), style=style)
