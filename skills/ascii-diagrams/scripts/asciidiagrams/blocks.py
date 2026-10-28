# Fence handling and disable directive after orchestkit (yonatangross/orchestkit); block selection rules are ours (MIT notice in THIRD_PARTY_NOTICES.md)
"""Find the diagram blocks in a text.

A block is the lines of one fenced code block (markdown) or of a whole file
(plain). Only blocks that look like diagrams are returned.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .glyphs import is_box_glyph

# Fences whose info string names one of these are code, not diagrams, unless
# they also hold MIN_BOX_GLYPHS box-drawing characters.
CODE_LANGS = frozenset("""
bash sh zsh shell console terminal fish powershell ps1 bat cmd
python py python3 js javascript jsx ts typescript tsx node json jsonc json5
yaml yml toml ini xml html css scss sass less sql graphql
c cpp cxx cc h hpp cs csharp java kotlin kt swift objc objective-c go golang
rust rs ruby rb php perl lua r scala dart haskell hs elixir ex clojure
diff patch dockerfile makefile make cmake gradle proto
mermaid plantuml dot graphviz latex tex csv
""".split())

MIN_BOX_GLYPHS = 3
MIN_ASCII_BORDERS = 2

_FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})\s*([^`]*)$")
_ASCII_SEGMENT = re.compile(r"\+[-=+]*[-=][-=+]*\+")
_DISABLE = re.compile(r"<!--\s*ascii-diagrams-disable:\s*([\w,\s-]*?)\s*-->")
_DISABLE_PLAIN = re.compile(r"ascii-diagrams-disable:\s*([\w,\s-]*?)\s*(?:-->|$)")


@dataclass
class Block:
    """One candidate diagram. `start_line` is the 1-based file line of lines[0]."""
    path: str
    start_line: int
    lines: list
    lang: str = ""
    disabled: set = field(default_factory=set)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def count_box_glyphs(lines) -> int:
    return sum(1 for line in lines for ch in line if is_box_glyph(ch))


def ascii_border_segments(line: str) -> list:
    """Spans (start, end) of the `+---+` segments of an ASCII border row, or [] if the row is not one.

    A border row starts and ends with a segment; between segments there is only
    space and connector text, never a `|` or a `+`.
    """
    s = line.rstrip()
    segs = [m.span() for m in _ASCII_SEGMENT.finditer(s)]
    if not segs:
        return []
    lead = len(s) - len(s.lstrip())
    if segs[0][0] != lead or segs[-1][1] != len(s):
        return []
    for (_, e0), (s1, _) in zip(segs, segs[1:]):
        if re.search(r"[|+]", s[e0:s1]):
            return []
    return segs


def is_ascii_border(line: str) -> bool:
    return bool(ascii_border_segments(line))


def count_ascii_borders(lines) -> int:
    return sum(1 for line in lines if is_ascii_border(line))


def is_diagram(lines, lang: str = "") -> bool:
    """3+ box glyphs, or 2+ ASCII border rows (not in a code-language fence)."""
    if count_box_glyphs(lines) >= MIN_BOX_GLYPHS:
        return True
    if lang.lower() in CODE_LANGS:
        return False
    return count_ascii_borders(lines) >= MIN_ASCII_BORDERS


def parse_disable(line: str, plain: bool = False) -> set:
    """Rule names from an `ascii-diagrams-disable: a,b` directive, or an empty set."""
    m = (_DISABLE_PLAIN if plain else _DISABLE).search(line)
    if not m:
        return set()
    return {r.strip() for r in m.group(1).split(",") if r.strip()}


def split_lines(text: str) -> list:
    """Split on \\n only (the way editors number lines), dropping a trailing \\r."""
    return [ln[:-1] if ln.endswith("\r") else ln for ln in text.split("\n")]


def _lang(info: str) -> str:
    token = re.split(r"[\s{,]", info.strip(), maxsplit=1)[0]
    return token.lower()


def extract(text: str, kind: str = "markdown", path: str = "") -> list:
    """Diagram blocks of `text`. kind: "markdown" (fenced blocks) or "plain" (the whole text)."""
    if kind not in ("markdown", "plain"):
        raise ValueError("kind must be 'markdown' or 'plain', not %r" % (kind,))
    lines = split_lines(text)
    if kind == "plain":
        disabled = set()
        for line in lines:
            disabled |= parse_disable(line, plain=True)
        if not is_diagram(lines):
            return []
        return [Block(path, 1, lines, "", disabled)]
    blocks = []
    fenced = set()
    i = 0
    n = len(lines)
    while i < n:
        m = _FENCE_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        fence, info = m.group(1), m.group(2)
        char, size = fence[0], len(fence)
        close = re.compile(r"^\s*" + re.escape(char) + "{%d,}\\s*$" % size)
        j = i + 1
        while j < n and not close.match(lines[j]):
            j += 1
        body = lines[i + 1:j]
        lang = _lang(info)
        if is_diagram(body, lang):
            disabled = parse_disable(lines[i - 1]) if i > 0 else set()
            blocks.append(Block(path, i + 2, body, lang, disabled))
        fenced.update(range(i, min(j, n - 1) + 1))
        i = j + 1
    blocks += _unfenced(lines, fenced, path)
    blocks.sort(key=lambda b: b.start_line)
    return blocks


_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
_INDENT = re.compile(r"^(?: {4}|\t)")
_PIPE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_PIPE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$")


def _has_glyph(line: str) -> bool:
    return any("\u2500" <= ch <= "\u257f" for ch in line)


_BACKTICKS = re.compile(r"`+")


def mask_code_spans(line: str) -> str:
    """`line` with every inline code span (backticks included) blanked to spaces, columns kept.

    A span opens at a backtick string and closes at the next backtick string of
    the same length (CommonMark); an opener with no closer is literal text.
    """
    runs = list(_BACKTICKS.finditer(line))
    if not runs:
        return line
    out = list(line)
    k = 0
    while k < len(runs):
        size = len(runs[k].group())
        close = next((m for m in runs[k + 1:] if len(m.group()) == size), None)
        if close is None:
            k += 1
            continue
        for c in range(runs[k].start(), close.end()):
            out[c] = " "
        k = runs.index(close) + 1
    return "".join(out)


def _unfenced(lines, fenced, path) -> list:
    """Diagram blocks outside fences: indented code blocks, and bare runs of box-drawing or border rows."""
    n = len(lines)
    usable = [True] * n  # False inside a fence or an HTML comment
    in_comment = False
    for i, line in enumerate(lines):
        if i in fenced:
            usable[i] = False
            continue
        if in_comment:
            usable[i] = False
            if "-->" in line:
                in_comment = False
            continue
        if "<!--" in line and "-->" not in line.split("<!--", 1)[1]:
            usable[i] = False
            in_comment = True
    blocks = []
    taken = set()

    def disabled_above(i):
        return parse_disable(lines[i - 1]) if i > 0 else set()

    # (a) indented code blocks: after a blank line, not a list continuation
    i = 0
    while i < n:
        if not (usable[i] and _INDENT.match(lines[i]) and lines[i].strip()):
            i += 1
            continue
        k = i - 1
        while k >= 0 and not lines[k].strip():
            k -= 1
        if i > 0 and lines[i - 1].strip():
            i += 1  # a paragraph continuation, not a code block
            continue
        if k >= 0 and _LIST_ITEM.match(lines[k]):
            i += 1
            continue
        j = i
        last = i
        while j < n and usable[j] and (not lines[j].strip() or _INDENT.match(lines[j])):
            if lines[j].strip():
                last = j
            j += 1
        body = [ln[1:] if ln.startswith("\t") else ln[4:] for ln in lines[i:last + 1]]
        if is_diagram(body):
            blocks.append(Block(path, i + 1, body, "", disabled_above(i)))
            taken.update(range(i, last + 1))
        i = last + 1

    # (b) bare runs of lines with a box glyph or an ASCII border row.
    # Glyphs inside inline code spans are quoted, not drawn; and a row of a
    # pipe table (one with a |---| separator row) is a table, not a diagram.
    masked = [mask_code_spans(ln) for ln in lines]
    table_row = set()
    k = 0
    while k < n:
        if not _PIPE_ROW.match(lines[k]):
            k += 1
            continue
        e = k
        while e < n and _PIPE_ROW.match(lines[e]):
            e += 1
        if any(_PIPE_SEP.match(lines[r]) and "-" in lines[r] for r in range(k, e)):
            table_row.update(range(k, e))
        k = e

    def member(i, run_has_border):
        if not usable[i] or i in taken or i in table_row:
            return False
        line = masked[i]
        if _has_glyph(line) or is_ascii_border(line):
            return True
        return run_has_border and bool(_PIPE_ROW.match(line)) and not _PIPE_SEP.match(line)

    i = 0
    while i < n:
        if not member(i, False):
            i += 1
            continue
        j = i
        has_border = False
        while j < n and member(j, has_border):
            has_border = has_border or is_ascii_border(lines[j])
            j += 1
        run = lines[i:j]
        mrun = masked[i:j]
        # trailing pipe rows after the last glyph or border row are not part of it
        while mrun and not (_has_glyph(mrun[-1]) or is_ascii_border(mrun[-1])):
            run.pop()
            mrun.pop()
        if len(run) >= 2 and is_diagram(mrun):
            blocks.append(Block(path, i + 1, run, "", disabled_above(i)))
        i = j
    return blocks
