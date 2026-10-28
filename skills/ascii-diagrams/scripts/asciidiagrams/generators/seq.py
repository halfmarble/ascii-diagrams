# Ported from kouko/monkey-skills ascii-graph-toolkit/skills/ascii-graph/scripts/gen_seq.py (MIT); see THIRD_PARTY_NOTICES.md
"""Sequence diagram: participant boxes, lifelines, one label row and one arrow row per message.

Lifelines run unbroken from header to footer. A message shaft starts on the
sender's lifeline with a tee and ends in an arrowhead in the cell before the
receiver's lifeline; arrows across non-adjacent participants cross the
lifelines between with the set's cross. A message
from a participant to itself is rejected.
"""
from __future__ import annotations

from ..width import clusters, display_width
from ._box import arrows, as_text, get_set, single_line

_GAP = 3
_LIFELINE_ROWS = 2


def render_seq(participants: "list[str]", messages: "list[dict]", style: str = "light") -> str:
    st = get_set(style)
    heads = arrows(style)
    if not participants:
        return ""
    for nm in participants:
        single_line(as_text(nm, "participant name"), "participant name")
    if len(set(participants)) != len(participants):
        raise ValueError("participant names must be unique: %r" % (participants,))
    for msg in messages:
        if not isinstance(msg, dict) or not all(k in msg for k in ("from", "to", "label")):
            raise ValueError("message needs from, to and label: %r" % (msg,))
        single_line(as_text(msg["label"], "message label"), "message label")
        for end in ("from", "to"):
            if msg[end] not in participants:
                raise ValueError("message %s unknown participant: %r" % (end, msg[end]))
        if msg["from"] == msg["to"]:
            raise ValueError("self-message not supported: %r -> %r" % (msg["from"], msg["to"]))

    interiors = [display_width(nm) + 2 for nm in participants]
    index_of = {nm: i for i, nm in enumerate(participants)}
    gaps = [_GAP] * (len(participants) - 1)

    def seg_dist(k: int) -> int:
        """Cells from lifeline k to lifeline k+1."""
        return (interiors[k] + 2 - (1 + interiors[k] // 2)) + gaps[k] + (1 + interiors[k + 1] // 2)

    # The label sits between two neighbouring lifelines of its arrow, so it
    # never covers one: widen the roomiest such gap until it fits with a
    # blank cell on each side.
    for msg in messages:
        i, j = index_of[msg["from"]], index_of[msg["to"]]
        lo, hi = min(i, j), max(i, j)
        k = max(range(lo, hi), key=seg_dist)
        deficit = display_width(msg["label"]) + 2 - (seg_dist(k) - 1)
        if deficit > 0:
            gaps[k] += deficit

    centers = []  # type: list[int]
    col = 0
    for idx, interior in enumerate(interiors):
        centers.append(col + 1 + interior // 2)
        col += interior + 2
        if idx < len(gaps):
            col += gaps[idx]
    total = col

    def join(segs: "list[str]") -> str:
        out = segs[0]
        for k, seg in enumerate(segs[1:]):
            out += " " * gaps[k] + seg
        return out

    top = join([st["tl"] + st["h"] * iw + st["tr"] for iw in interiors])
    name = join([st["v"] + " " + nm + " " + st["v"] for nm in participants])
    bottom_segs = []
    for iw in interiors:
        chars = [st["h"]] * iw
        chars[iw // 2] = st["tee_d"]
        bottom_segs.append(st["bl"] + "".join(chars) + st["br"])
    lines = [top, name, join(bottom_segs)]

    def lifeline_row() -> "list[str]":
        row = [" "] * total
        for c in centers:
            row[c] = st["v"]
        return row

    for _ in range(_LIFELINE_ROWS):
        lines.append("".join(lifeline_row()).rstrip())
    center_of = dict(zip(participants, centers))

    for msg in messages:
        src, dst = center_of[msg["from"]], center_of[msg["to"]]
        lo, hi = min(src, dst), max(src, dst)
        label = msg["label"]
        lw = display_width(label)
        row = lifeline_row()
        # the neighbouring lifelines inside [lo, hi] that leave the most room
        between = [c for c in centers if lo <= c <= hi]
        left, right = max(zip(between, between[1:]), key=lambda p: p[1] - p[0])
        start = left + 1 + (right - left - 1 - lw) // 2
        col = start
        for cl, w in clusters(label):
            if w == 0:
                if col > start:
                    row[col - 1] += cl
                continue
            row[col] = cl
            for k in range(1, w):
                row[col + k] = ""
            col += w
        lines.append("".join(row).rstrip())
        arrow = lifeline_row()
        for c in range(lo + 1, hi):
            arrow[c] = st["cross"] if c in centers else st["h"]
        if dst > src:
            arrow[src] = st["tee_r"]
            arrow[dst - 1] = heads["right"]
        else:
            arrow[src] = st["tee_l"]
            arrow[dst + 1] = heads["left"]
        lines.append("".join(arrow).rstrip())
    return "\n".join(l.rstrip() for l in lines)
