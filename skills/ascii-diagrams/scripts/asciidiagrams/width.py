# Ported from kouko/monkey-skills ascii-graph-toolkit/skills/ascii-graph/scripts/width.py (MIT); see THIRD_PARTY_NOTICES.md
"""Display width in terminal cells, stdlib only (no wcwidth).

Policy:
  - controls and format characters (Cc, Cf, lone combining marks) -> 0 cells
  - East Asian Wide / Fullwidth                                  -> 2 cells
  - emoji ZWJ sequences, VS16 clusters, flags                    -> 2 cells
  - East Asian Ambiguous                                         -> 1 cell (2 with ambiguous_wide)
  - box drawing U+2500-257F and blocks U+2580-259F               -> always 1 cell
  - everything else                                              -> 1 cell

Widths of emoji and of characters newer than the running Python's Unicode
tables differ between terminals; stability() flags them as "unstable".
"""
from __future__ import annotations

import unicodedata

ZWJ = "\u200d"
VS15 = "\ufe0e"
VS16 = "\ufe0f"


def _is_regional(ch: str) -> bool:
    return 0x1F1E6 <= ord(ch) <= 0x1F1FF


def _is_modifier(ch: str) -> bool:
    return 0x1F3FB <= ord(ch) <= 0x1F3FF


def _is_extender(ch: str) -> bool:
    """True for a character that attaches to the cluster before it."""
    if ch in (VS15, VS16) or _is_modifier(ch):
        return True
    if 0xE0020 <= ord(ch) <= 0xE007F:  # tag characters (subdivision flags)
        return True
    return unicodedata.category(ch) in ("Mn", "Me")


def _is_control(ch: str) -> bool:
    return unicodedata.category(ch) in ("Cc", "Cf", "Cs") or ch == "\u2028" or ch == "\u2029"


def clusters(s: str) -> "list[tuple[str, int]]":
    """Split s into grapheme-ish clusters, each with its width in cells."""
    out = []  # type: list[str]
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        j = i + 1
        if _is_control(ch):
            # A control or format character is its own zero-width cluster,
            # except ZWJ / variation selectors, which join a previous one below.
            out.append(ch)
            i = j
            continue
        if _is_regional(ch) and j < n and _is_regional(s[j]):
            j += 1
        while j < n:
            c = s[j]
            if c == ZWJ:
                j += 1
                if j < n and not _is_control(s[j]):
                    j += 1  # the joined character
                continue
            if _is_extender(c):
                j += 1
                continue
            break
        out.append(s[i:j])
        i = j
    return [(c, cell_width(c)) for c in out]


def _char_cells(ch: str, ambiguous_wide: bool) -> int:
    o = ord(ch)
    if 0x2500 <= o <= 0x259F:
        return 1
    if _is_control(ch):
        return 0
    if unicodedata.category(ch) in ("Mn", "Me"):
        return 0
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ("W", "F"):
        return 2
    if eaw == "A":
        return 2 if ambiguous_wide else 1
    return 1


def cell_width(cluster: str, ambiguous_wide: bool = False) -> int:
    """Cells taken by one cluster (as produced by clusters())."""
    if not cluster:
        return 0
    base = cluster[0]
    if len(cluster) == 1:
        return _char_cells(base, ambiguous_wide)
    if _is_control(base):
        return 0
    if 0x2500 <= ord(base) <= 0x259F:
        return 1
    if _is_regional(base) and _is_regional(cluster[1]):
        return 2  # flag
    if VS16 in cluster:
        return 2
    if ZWJ in cluster and (ord(base) >= 0x1F000 or unicodedata.east_asian_width(base) == "W"):
        return 2
    if unicodedata.category(base) in ("Mn", "Me"):
        return 0
    return _char_cells(base, ambiguous_wide)


def display_width(s: str, ambiguous_wide: bool = False) -> int:
    """Total cells of a string."""
    return sum(cell_width(c, ambiguous_wide) for c, _ in clusters(s))


def _is_emoji_base(ch: str) -> bool:
    o = ord(ch)
    if o >= 0x1F000:
        return True
    return unicodedata.east_asian_width(ch) == "W" and 0x2300 <= o <= 0x2BFF


def stability(cluster: str) -> str:
    """"stable", "ambiguous" or "unstable": how sure we are of the cell width.

    Unstable: emoji, ZWJ sequences, VS16 clusters, flags, and characters
    unassigned in the running unicodedata (newer than unidata_version).
    Ambiguous: East Asian Ambiguous width characters.
    """
    if not cluster:
        return "stable"
    for ch in cluster:
        if unicodedata.category(ch) == "Cn":
            return "unstable"
    if ZWJ in cluster or VS16 in cluster or _is_regional(cluster[0]):
        return "unstable"
    if _is_emoji_base(cluster[0]):
        return "unstable"
    base = cluster[0]
    if 0x2500 <= ord(base) <= 0x259F:
        return "stable"
    if unicodedata.east_asian_width(base) == "A":
        return "ambiguous"
    return "stable"


def split_lines(label: str) -> "list[str]":
    """Split a label into at least one physical line, no embedded controls.

    str.splitlines() breaks on \\n, \\r, \\r\\n (and \\v, \\f), so a bare CR
    becomes a real break; left embedded it is a zero-width cursor move that
    passes width checks and corrupts terminal alignment. "" gives [""].
    """
    return label.splitlines() or [""]
