# Ported from kouko/monkey-skills ascii-graph-toolkit/skills/ascii-graph/scripts/checks_{seam,kink,table}.py and terrylica/cc-skills plugins/doc-tools/skills/ascii-diagram-validator/scripts/check_ascii_alignment.py (MIT); see THIRD_PARTY_NOTICES.md
"""Checks on a diagram block, all on display cells (never string indexes).

Rules: connect box kink arrowhead table seam width unstable ambiguous
(on by default) and mixed-set mixed-arrows (opt in).
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from .blocks import Block, ascii_border_segments, extract
from .glyphs import ARMS, ARROWS, ASCII_ARROWS, is_box_glyph
from .grid import Grid
from .width import display_width, stability

DEFAULT_RULES = frozenset(
    "connect box kink arrowhead table seam width unstable ambiguous".split())
ALL_RULES = DEFAULT_RULES | frozenset(["mixed-set", "mixed-arrows"])

ERROR, WARNING, INFO = "error", "warning", "info"

_OPP = {"u": "d", "d": "u", "l": "r", "r": "l"}
_DELTA = {"u": (-1, 0), "d": (1, 0), "l": (0, -1), "r": (0, 1)}
_UD = frozenset("ud")
_LR = frozenset("lr")
_EMPTY = frozenset()
_DR = frozenset("dr")
_VERTICAL_ARROWS = frozenset("▼▲")
_ASCII_LINE = frozenset("-=|+")
_TREE_ROW = re.compile(r"[├└╟╙┝┕┠┖┣┗╞╘╠╚╰][─━═-]+ +[^\s─-╿+|-]")


@dataclass(frozen=True)
class Finding:
    """One result. `line` is the 1-based file line, `col` the 1-based display column."""
    line: int
    col: int
    severity: str
    rule: str
    message: str
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        return {"line": self.line, "col": self.col, "severity": self.severity,
                "rule": self.rule, "message": self.message,
                "suggestion": self.suggestion}


class _View:
    """A Grid plus the arm lookups the checks share."""

    def __init__(self, lines, ambiguous_wide: bool):
        self.g = Grid(lines, ambiguous_wide)
        self._arms = {}

    def arms(self, r: int, c: int) -> frozenset:
        """Directions in which the cell is a line. ASCII + counts only with 2+ line neighbours."""
        key = (r, c)
        if key not in self._arms:
            self._arms[key] = self._compute(r, c)
        return self._arms[key]

    def _compute(self, r, c):
        ch = self.g.at(r, c)
        if not ch:
            return _EMPTY
        if ch in ("-", "="):
            return _LR
        if ch == "|":
            return _UD
        if ch == "+":
            found = frozenset(d for d in "udlr" if self._provides(r + _DELTA[d][0], c + _DELTA[d][1], _OPP[d]))
            return found if len(found) >= 2 else _EMPTY
        return ARMS.get(ch, _EMPTY) if is_box_glyph(ch) else _EMPTY

    def _provides(self, r, c, arm) -> bool:
        ch = self.g.at(r, c)
        if not ch:
            return False
        if ch == "+":
            return True
        if ch in ("-", "="):
            return arm in "lr"
        if ch == "|":
            return arm in "ud"
        return is_box_glyph(ch) and arm in ARMS.get(ch, _EMPTY)

    def is_vertical(self, ch) -> bool:
        """A pure vertical line glyph (light, heavy, double, dashed) or ASCII |."""
        if not ch:
            return False
        if ch == "|":
            return True
        return is_box_glyph(ch) and ARMS.get(ch) == _UD


def _mk(block, row, col, severity, rule, message, suggestion=None):
    return Finding(block.start_line + row, col + 1, severity, rule, message, suggestion)


def _is_tree(lines) -> bool:
    rows = [ln.rstrip() for ln in lines if ln.strip()]
    if not rows:
        return False
    hits = sum(1 for ln in rows if _TREE_ROW.search(ln))
    return hits / len(rows) > 0.20


# --------------------------------------------------------------------- connect

def _meets(v: _View, r: int, c: int, d: str) -> str:
    """How the cell at (r, c) answers a line arm pointing at it: ok, gap, text or mismatch."""
    n = v.g.at(r, c)
    if n is None or n == " ":
        return "gap"
    if n == "":
        return "text"
    if ARROWS.get(n) == d or ASCII_ARROWS.get(n) == d:
        return "ok"
    a = v.arms(r, c)
    if _OPP[d] in a:
        return "ok"
    return "mismatch" if a else "text"


def check_connect(block, v):
    out = []
    g = v.g
    for r in range(g.height):
        for col, text, _ in g.row_clusters(r):
            if len(text) != 1 or not is_box_glyph(text):
                continue
            a = ARMS.get(text)
            if not a:
                continue
            strict = len(a) == 4 or (len(a) == 2 and a not in (_UD, _LR))
            bad = []
            for d in "udlr":
                if d not in a:
                    continue
                dr, dc = _DELTA[d]
                verdict = _meets(v, r + dr, col + dc, d)
                if verdict == "mismatch" or (strict and verdict != "ok"):
                    n = g.at(r + dr, col + dc)
                    shown = "nothing" if not n or n == " " else repr(n)
                    bad.append((d, shown))
            if bad:
                names = {"u": "up", "d": "down", "l": "left", "r": "right"}
                detail = ", ".join("%s arm meets %s" % (names[d], s) for d, s in bad)
                out.append(_mk(block, r, col, ERROR, "connect",
                               "'%s' does not connect: %s" % (text, detail),
                               "move the neighbouring border so this arm meets a glyph that continues it"))
    return out


# ------------------------------------------------------------------------- box

def _trace_right(v, r, c0, want):
    """Walk right from the corner at (r, c0). ("ok", c) at the end glyph (it has arm `want`), else ("open", c)."""
    g = v.g
    width = g.width(r)
    c = c0 + 1
    while True:
        if c >= width:
            return ("open", c)
        a = v.arms(r, c)
        if "l" in a:
            if "r" in a:
                c += 1
                continue
            return ("ok", c) if want in a else ("open", c)
        if a:
            return ("open", c)
        # a label inside the border: text up to the next line glyph with a left arm
        c2 = c
        seen = False
        while c2 < width and not v.arms(r, c2):
            cell = g.at(r, c2)
            if cell and cell.strip():
                seen = True
            c2 += 1
        if c2 < width and seen and "l" in v.arms(r, c2):
            c = c2
            continue
        return ("open", c)


def _trace_down(v, r0, c, want):
    """Walk down from the corner at (r0, c). ("ok", r) at the end glyph (it has arm `want`), else ("open", r)."""
    r = r0 + 1
    height = v.g.height
    while True:
        if r >= height:
            return ("open", r)
        a = v.arms(r, c)
        if "u" not in a:
            return ("open", r)
        if "d" in a:
            r += 1
            continue
        return ("ok", r) if want in a else ("open", r)


def _ascii_right(v, r, c0):
    """Walk right along an ASCII top or bottom side from the `+` at (r, c0). ("ok", c) at the next `+`, else ("open", c)."""
    g = v.g
    width = g.width(r)
    c = c0 + 1
    while c < width:
        ch = g.at(r, c)
        if ch == "+":
            if g.at(r, c + 1) in ("-", "="):  # a T junction: the side goes on
                c += 1
                continue
            return ("ok", c) if c > c0 + 1 else ("open", c)
        if ch in ("-", "="):
            c += 1
            continue
        # a label inside the border: text up to the next dash or plus
        c2 = c
        seen = False
        while c2 < width and g.at(r, c2) not in ("-", "=", "+", "|"):
            cell = g.at(r, c2)
            if cell and cell.strip():
                seen = True
            c2 += 1
        if c2 < width and seen and g.at(r, c2) in ("-", "=", "+"):
            c = c2
            continue
        return ("open", c)
    return ("open", c)


def _ascii_down(v, r0, c):
    """Walk down a `|` side from the `+` at (r0, c). ("ok", r) at the next `+`, else ("open", r)."""
    r = r0 + 1
    while r < v.g.height:
        ch = v.g.at(r, c)
        if ch == "+":
            return ("ok", r) if r > r0 + 1 else ("open", r)
        if ch != "|":
            return ("open", r)
        r += 1
    return ("open", r)


def check_ascii_box(block, v, skip):
    """Boxes drawn with `+`, `-`, `=` and `|`. A top-left corner is a `+` with a dash to its right and a `|` below."""
    out = []
    g = v.g
    for r in range(g.height):
        for col, text, _ in g.row_clusters(r):
            if text != "+" or (r, col) in skip:
                continue
            if g.at(r, col + 1) not in ("-", "=") or g.at(r + 1, col) != "|":
                continue
            if g.at(r, col - 1) in ("-", "="):
                continue  # a T junction in the middle of a side, e.g. a lifeline hanging from a box
            top = _ascii_right(v, r, col)
            left = _ascii_down(v, r, col)
            top_ok, left_ok = top[0] == "ok", left[0] == "ok"
            if not top_ok and not left_ok:
                continue
            problem = None
            if top_ok and left_ok:
                tr_c, bl_r = top[1], left[1]
                right = _ascii_down(v, r, tr_c)
                if right[0] != "ok":
                    problem = (right[1], tr_c, "right side opens here")
                elif right[1] != bl_r:
                    problem = (right[1], tr_c, "right side ends on a different row than the left side (row %d)" % (bl_r + 1))
                else:
                    bottom = _ascii_right(v, bl_r, col)
                    if bottom[0] != "ok":
                        problem = (bl_r, bottom[1], "bottom side opens here")
                    elif bottom[1] != tr_c:
                        problem = (bl_r, bottom[1], "bottom side ends at column %d, not under the top-right corner at %d" % (bottom[1] + 1, tr_c + 1))
            elif top_ok:
                right = _ascii_down(v, r, top[1])
                if right[0] == "ok":
                    problem = (left[1], col, "left side opens here")
            else:
                bottom = _ascii_right(v, left[1], col)
                if bottom[0] == "ok":
                    problem = (r, top[1], "top side opens here")
            if problem:
                pr, pc, why = problem
                out.append(_mk(block, pr, pc, ERROR, "box",
                               "box from line %d col %d: %s" % (block.start_line + r, col + 1, why),
                               "close the box: every side must reach the next corner"))
    return out


def check_box(block, v):
    out = []
    g = v.g
    handled = set()
    for r in range(g.height):
        for col, text, _ in g.row_clusters(r):
            if len(text) != 1:
                continue
            if v.arms(r, col) != _DR:
                continue
            top = _trace_right(v, r, col, "d")
            left = _trace_down(v, r, col, "r")
            top_ok, left_ok = top[0] == "ok", left[0] == "ok"
            if not top_ok and not left_ok:
                continue  # a bend of a connector, not a box
            problem = None  # (row, col, message)
            if top_ok and left_ok:
                tr_c, bl_r = top[1], left[1]
                right = _trace_down(v, r, tr_c, "l")
                if right[0] != "ok":
                    problem = (right[1], tr_c, "right side opens here")
                elif right[1] != bl_r:
                    problem = (right[1], tr_c, "right side ends on a different row than the left side (row %d)" % (bl_r + 1))
                else:
                    bottom = _trace_right(v, bl_r, col, "u")
                    if bottom[0] != "ok":
                        problem = (bl_r, bottom[1], "bottom side opens here")
                    elif bottom[1] != tr_c:
                        problem = (bl_r, bottom[1], "bottom side ends at column %d, not under the top-right corner at %d" % (bottom[1] + 1, tr_c + 1))
            elif top_ok:
                right = _trace_down(v, r, top[1], "l")
                if right[0] == "ok":
                    problem = (left[1], col, "left side opens here")
            else:
                bottom = _trace_right(v, left[1], col, "u")
                if bottom[0] == "ok":
                    problem = (r, top[1], "top side opens here")
            if problem:
                handled.add((r, col))
                pr, pc, why = problem
                out.append(_mk(block, pr, pc, ERROR, "box",
                               "box from line %d col %d: %s" % (block.start_line + r, col + 1, why),
                               "close the box: every side must reach the next corner"))
    return out + check_ascii_box(block, v, handled)


# ------------------------------------------------------------------ kink, seam

def _structural(v, r):
    """col -> glyph for line glyphs and vertical arrowheads on row r."""
    cols = {}
    for col, text, _ in v.g.row_clusters(r):
        if len(text) == 1 and (is_box_glyph(text) and text in ARMS or text in "▼▲↑↓"):
            cols[col] = text
    return cols


def _is_junction(ch) -> bool:
    a = ARMS.get(ch) if is_box_glyph(ch) else None
    return bool(a) and a not in (_UD, _LR) and len(a) >= 2


def check_kink(block, v):
    out = []
    g = v.g
    rows = [_structural(v, r) for r in range(g.height)]
    for r in range(g.height - 1):
        below = rows[r + 1]
        if not below:
            continue
        for col, ch in rows[r].items():
            plain = (is_box_glyph(ch) and ARMS.get(ch) == _UD) or ch in _VERTICAL_ARROWS
            if not plain or col in below:
                continue
            for delta in (-1, 1):
                bc = col + delta
                if bc in below and not _is_junction(below[bc]):
                    out.append(_mk(block, r + 1, bc, ERROR, "kink",
                                   "seam kink: connector drifts from column %d to column %d with no junction glyph" % (col + 1, bc + 1),
                                   "put the connector in the same column on both rows, or use a junction glyph"))
    return out


def check_arrowhead(block, v):
    out = []
    g = v.g
    for r in range(g.height):
        for col, text, _ in g.row_clusters(r):
            if text not in _VERTICAL_ARROWS:
                continue
            tgt = r + (1 if text == "▼" else -1)
            if not 0 <= tgt < g.height:
                continue
            cols = [c for c, t, _ in g.row_clusters(tgt) if len(t) == 1 and is_box_glyph(t) and t in ARMS]
            if not cols:
                continue
            lo, hi = min(cols), max(cols)
            if not lo <= col <= hi:
                out.append(_mk(block, r, col, ERROR, "arrowhead",
                               "arrowhead '%s' at column %d misses the box span %d..%d on line %d" % (text, col + 1, lo + 1, hi + 1, block.start_line + tgt),
                               "move the arrowhead into the span of the box it points at"))
    return out


def check_seam(block, v):
    out = []
    g = v.g
    for r in range(g.height):
        for col, text, _ in g.row_clusters(r):
            if len(text) != 1 or not is_box_glyph(text) or ARMS.get(text) != _UD:
                continue
            up = v.arms(r - 1, col)
            dn = v.arms(r + 1, col)
            ua, da = g.at(r - 1, col), g.at(r + 1, col)
            anchored = ("d" in up or ARROWS.get(ua) in ("u", "d")
                        or "u" in dn or ARROWS.get(da) in ("u", "d"))
            if not anchored:
                out.append(_mk(block, r, col, ERROR, "seam",
                               "'%s' at column %d connects to nothing vertically" % (text, col + 1),
                               "align this border with the rows above and below"))
    return out


# ----------------------------------------------------------------------- table

def _row_frame(v, r):
    """(kind, left, right, ascii) for a frame row, or None. kind: content or border."""
    cl = [(c, t) for c, t, _ in v.g.row_clusters(r) if t.strip()]
    if len(cl) < 2:
        return None
    (c0, t0), (c1, t1) = cl[0], cl[-1]
    line = v.g.lines[r]
    if v.is_vertical(t0) and v.is_vertical(t1):
        return ("content", c0, c1, t0 == "|")
    if len(ascii_border_segments(line)) == 1:
        return ("border", c0, c1, True)
    a0, a1 = ARMS.get(t0, _EMPTY) if is_box_glyph(t0) else _EMPTY, ARMS.get(t1, _EMPTY) if is_box_glyph(t1) else _EMPTY
    if "r" in a0 and ("d" in a0 or "u" in a0) and "l" in a1 and ("d" in a1 or "u" in a1):
        return ("border", c0, c1, False)
    return None


def _modal(values):
    return Counter(values).most_common(1)[0][0]


def check_table(block, v):
    out = []
    g = v.g
    frames = [_row_frame(v, r) for r in range(g.height)]
    groups, cur = [], []
    for r, f in enumerate(frames):
        if f is None:
            if cur:
                groups.append(cur)
            cur = []
            continue
        first_arms = ARMS.get(g.at(r, f[1]), _EMPTY) if not f[3] else _EMPTY
        if cur:
            same = frames[cur[-1]][1] == f[1] and frames[cur[-1]][3] == f[3]
            top = f[0] == "border" and first_arms == _DR
            if not same or top:
                groups.append(cur)
                cur = []
        cur.append(r)
        if f[0] == "border" and "d" not in first_arms and "u" in first_arms and not f[3]:
            groups.append(cur)  # a bottom border closes the table
            cur = []
    if cur:
        groups.append(cur)
    for grp in groups:
        content = [r for r in grp if frames[r][0] == "content"]
        borders = [r for r in grp if frames[r][0] == "border"]
        ascii_group = frames[grp[0]][3]
        if ascii_group and not borders:
            continue
        if len(content) >= 2:
            pass
        elif len(content) == 1 and borders:
            if not any(frames[b][2] == frames[content[0]][2] for b in borders):
                continue
        else:
            continue
        ref = _modal([frames[b][2] for b in borders] if borders else [frames[r][2] for r in grp])
        for r in grp:
            right = frames[r][2]
            if right != ref:
                out.append(_mk(block, r, right, ERROR, "table",
                               "table row ends at column %d, but the block edge is at column %d" % (right + 1, ref + 1),
                               "pad this row by display cells (CJK and emoji take 2), not by characters"))
    return out


# ------------------------------------------------------------ width and styles

def check_width(block, v, max_width):
    out = []
    for r, line in enumerate(v.g.lines):
        w = display_width(line.rstrip(), v.g.ambiguous_wide)
        if w > max_width:
            out.append(_mk(block, r, max_width, WARNING, "width",
                           "line is %d cells wide, over the limit of %d" % (w, max_width),
                           "shorten the line or split the diagram"))
    return out


def _is_frame_cell(v, r, c, text) -> bool:
    if text == "|":
        return True
    return is_box_glyph(text) and _UD <= ARMS.get(text, _EMPTY)


def check_stability(block, v, rules):
    out = []
    g = v.g
    for r in range(g.height):
        cl = g.row_clusters(r)
        frames = [c for c, t, _ in cl if len(t) == 1 and _is_frame_cell(v, r, c, t)]
        if not frames:
            continue
        last = max(frames)
        for col, text, w in cl:
            if col >= last:
                continue
            st = stability(text)
            if st == "unstable" and "unstable" in rules:
                out.append(_mk(block, r, col, WARNING, "unstable",
                               "'%s' has a terminal-dependent width (%d cells here) and sits left of a frame glyph" % (text, w),
                               "use a plain symbol, or keep this text outside the frame"))
            elif st == "ambiguous" and "ambiguous" in rules:
                out.append(_mk(block, r, col, INFO, "ambiguous",
                               "'%s' is East Asian ambiguous width and sits left of a frame glyph" % (text,),
                               "prefer a character of fixed width in framed rows"))
    return out


def _corner_set(ch):
    name = unicodedata.name(ch, "")
    if "HEAVY" in name:
        return "heavy"
    if "DOUBLE" in name:
        return "double"
    if "ARC" in name:
        return "rounded"
    return "light"


def check_mixed_set(block, v):
    seen = []
    for r in range(v.g.height):
        for col, text, _ in v.g.row_clusters(r):
            if len(text) == 1 and is_box_glyph(text):
                a = ARMS.get(text, _EMPTY)
                if len(a) == 2 and a not in (_UD, _LR):
                    seen.append((r, col, _corner_set(text)))
    sets = Counter(s for _, _, s in seen)
    if len(sets) < 2:
        return []
    major = sets.most_common(1)[0][0]
    r, col, s = next(x for x in seen if x[2] != major)
    return [_mk(block, r, col, INFO, "mixed-set",
                "corners from several sets (%s); this one is %s" % (", ".join(sorted(sets)), s),
                "use one corner set per diagram")]


def _arrow_family(ch):
    if ch in "▼▲►◄▶◀":
        return "triangle"
    if ch in "→←↑↓":
        return "arrow"
    return None


def check_mixed_arrows(block, v):
    seen = []
    for r in range(v.g.height):
        for col, text, _ in v.g.row_clusters(r):
            fam = _arrow_family(text) if len(text) == 1 else None
            if fam:
                seen.append((r, col, fam))
    fams = Counter(f for _, _, f in seen)
    if len(fams) < 2:
        return []
    major = fams.most_common(1)[0][0]
    r, col, f = next(x for x in seen if x[2] != major)
    return [_mk(block, r, col, INFO, "mixed-arrows",
                "arrowheads from several families (%s)" % ", ".join(sorted(fams)),
                "use one arrow style per diagram")]


# ------------------------------------------------------------------- entry points

def check_block(block: Block, rules=DEFAULT_RULES, max_width: int = 80,
                ambiguous_wide: bool = False) -> list:
    rules = set(rules)
    off = {r.lower() for r in block.disabled}
    if "all" in off:
        return []
    v = _View(block.lines, ambiguous_wide)
    tree = _is_tree(block.lines)
    found = []
    if "connect" in rules and not tree:
        found += check_connect(block, v)
    if "box" in rules and not tree:
        found += check_box(block, v)
    if "kink" in rules:
        found += check_kink(block, v)
    if "arrowhead" in rules:
        found += check_arrowhead(block, v)
    if "table" in rules:
        found += check_table(block, v)
    if "seam" in rules:
        found += check_seam(block, v)
    if "width" in rules:
        found += check_width(block, v, max_width)
    if "unstable" in rules or "ambiguous" in rules:
        found += check_stability(block, v, rules)
    if "mixed-set" in rules:
        found += check_mixed_set(block, v)
    if "mixed-arrows" in rules:
        found += check_mixed_arrows(block, v)
    seen = set()
    result = []
    for f in sorted(found, key=lambda f: (f.line, f.col, f.rule)):
        key = (f.line, f.col, f.rule)
        if key in seen or f.rule in off:
            continue
        seen.add(key)
        result.append(f)
    return result


def check_text(text: str, path: str = "", kind: str = "markdown", **kw) -> list:
    """All findings of every diagram block in `text`, ordered by line and column."""
    found = []
    for block in extract(text, kind, path):
        found += check_block(block, **kw)
    return sorted(found, key=lambda f: (f.line, f.col, f.rule))
