"""Shared helpers for the generators: style lookup, centring, padding, boxes.

All padding is computed in display cells (width.display_width), never in
characters, so wide (CJK) labels align with narrow ones.
"""
from __future__ import annotations

from ..glyphs import SETS
from ..width import display_width, split_lines

STYLES = ("light", "heavy", "double", "rounded", "ascii")

# Arrowheads and bar fill per style; the ASCII style stays ASCII-only.
_ARROWS = {
    "down": "▼", "right": "►", "left": "◄",
}
_ASCII_ARROWS = {"down": "v", "right": ">", "left": "<"}


def get_set(style: str) -> "dict[str, str]":
    """Glyph set for a style name; ValueError for an unknown one."""
    if style not in STYLES:
        raise ValueError("unknown style: %r (expected one of %s)" % (style, ", ".join(STYLES)))
    return dict(SETS[style])


def arrows(style: str) -> "dict[str, str]":
    get_set(style)
    return dict(_ASCII_ARROWS if style == "ascii" else _ARROWS)


def bar_fill(style: str) -> str:
    get_set(style)
    return "#" if style == "ascii" else "█"


def center(label: str, interior: int) -> str:
    """Pad label to `interior` cells, roughly centred; the odd cell goes right."""
    slack = interior - display_width(label)
    left = slack // 2
    return " " * left + label + " " * (slack - left)


def pad(label: str, width: int) -> str:
    """Left-align label, right-pad with spaces to `width` cells."""
    return label + " " * (width - display_width(label))


def single_line(text: str, what: str) -> str:
    """Return text unchanged, or raise ValueError when it holds a line break."""
    if split_lines(text) != [text]:
        raise ValueError("line break not supported in %s: %r" % (what, text))
    return text


def as_text(value: object, what: str) -> str:
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (what, value))
    return value


def box(lines: "list[str]", interior: int, st: "dict[str, str]") -> "list[str]":
    """A framed box: each line centred in `interior` cells."""
    out = [st["tl"] + st["h"] * interior + st["tr"]]
    for line in lines:
        out.append(st["v"] + center(line, interior) + st["v"])
    out.append(st["bl"] + st["h"] * interior + st["br"])
    return out
