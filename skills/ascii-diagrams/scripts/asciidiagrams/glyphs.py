# Arm model and glyph tables after terrylica/cc-skills plugins/doc-tools/skills/ascii-diagram-validator/scripts/check_ascii_alignment.py (MIT); see THIRD_PARTY_NOTICES.md
"""Box-drawing glyph taxonomy: which sides ("u" "d" "l" "r") each glyph reaches.

ARMS is generated from the Unicode names of U+2500-257F, so it is complete
rather than hand-typed. Diagonals (U+2571-2573) have no arms and are left out.
"""
from __future__ import annotations

import unicodedata

_DIRS = {"UP": "u", "DOWN": "d", "LEFT": "l", "RIGHT": "r"}


def _build_arms() -> "dict[str, frozenset[str]]":
    arms = {}  # type: dict[str, frozenset[str]]
    for code in range(0x2500, 0x2580):
        ch = chr(code)
        name = unicodedata.name(ch, "")
        if "DIAGONAL" in name:
            continue
        found = set()
        for word in name.split():
            if word in _DIRS:
                found.add(_DIRS[word])
            elif word == "VERTICAL":
                found.update("ud")
            elif word == "HORIZONTAL":
                found.update("lr")
        if found:
            arms[ch] = frozenset(found)
    # plain ASCII line characters
    arms["-"] = frozenset("lr")
    arms["="] = frozenset("lr")
    arms["|"] = frozenset("ud")
    arms["+"] = frozenset("udlr")
    return arms


ARMS = _build_arms()  # type: dict[str, frozenset[str]]

# Direction each arrowhead points. The ASCII heads (ASCII_ARROWS) are separate:
# they count as arrows only next to a line, so a checker consults them
# explicitly instead of treating every "v" or ">" as a head.
ARROWS = {
    "▼": "d", "▲": "u", "►": "r", "◄": "l",
    "▶": "r", "◀": "l",
    "→": "r", "←": "l", "↑": "u", "↓": "d",
}  # type: dict[str, str]

ASCII_ARROWS = {"v": "d", "^": "u", ">": "r", "<": "l"}  # type: dict[str, str]

# Named by use. Keys: h v (lines), tl tr bl br (corners), tee_r (like the
# tee with its stem to the right), tee_l, tee_d, tee_u, cross.
SETS = {
    "light": {"h": "─", "v": "│", "tl": "┌", "tr": "┐",
              "bl": "└", "br": "┘", "tee_r": "├",
              "tee_l": "┤", "tee_d": "┬", "tee_u": "┴",
              "cross": "┼"},
    "heavy": {"h": "━", "v": "┃", "tl": "┏", "tr": "┓",
              "bl": "┗", "br": "┛", "tee_r": "┣",
              "tee_l": "┫", "tee_d": "┳", "tee_u": "┻",
              "cross": "╋"},
    "double": {"h": "═", "v": "║", "tl": "╔", "tr": "╗",
               "bl": "╚", "br": "╝", "tee_r": "╠",
               "tee_l": "╣", "tee_d": "╦", "tee_u": "╩",
               "cross": "╬"},
    "rounded": {"h": "─", "v": "│", "tl": "╭", "tr": "╮",
                "bl": "╰", "br": "╯", "tee_r": "├",
                "tee_l": "┤", "tee_d": "┬", "tee_u": "┴",
                "cross": "┼"},
    "ascii": {"h": "-", "v": "|", "tl": "+", "tr": "+", "bl": "+", "br": "+",
              "tee_r": "+", "tee_l": "+", "tee_d": "+", "tee_u": "+",
              "cross": "+"},
}  # type: dict[str, dict[str, str]]

# Derived groups (all from ARMS, so they cannot drift from it).
VERTICALS = frozenset(c for c, a in ARMS.items() if a == frozenset("ud"))
HORIZONTALS = frozenset(c for c, a in ARMS.items() if a == frozenset("lr"))
CORNERS = frozenset(c for c, a in ARMS.items()
                    if len(a) == 2 and a not in (frozenset("ud"), frozenset("lr")))
TEES = frozenset(c for c, a in ARMS.items() if len(a) == 3)


def is_box_glyph(ch: str) -> bool:
    """True for a glyph in U+2500-257F (ASCII line characters excluded)."""
    return len(ch) == 1 and 0x2500 <= ord(ch) <= 0x257F
