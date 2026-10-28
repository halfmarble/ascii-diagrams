---
name: ascii-diagrams
description: Use before drawing any box diagram, table, flow, tree or architecture sketch in text, whether in a chat reply, a Markdown doc, a PR description or a code comment. Required when labels contain CJK text or emoji, or the drawing has three or more boxes. Generates aligned diagrams and checks hand-drawn ones.
---

# ascii-diagrams

Text diagrams break in one way: a border lands one column off. The cause is almost always a
width mistake (a CJK character is two cells, an emoji is unpredictable) or a hand-counted
border. This skill makes the tool do the counting.

The tool is `python3 "${CLAUDE_SKILL_DIR}/scripts/asciid.py"` (stdlib only, Python 3.9+).
Call it `asciid` below.

## 1. Route the request

| You need | Do this |
|---|---|
| table, flow, tree, bar chart, layered architecture, sequence | Generate it: `asciid gen <shape>` with a JSON payload on stdin. Check the output (section 3), then paste it unchanged. |
| anything else (custom layout, side-by-side boxes, annotated sketch) | Draw by hand, then run `asciid check` and fix every error until it exits 0. |
| class, ER, state or gantt diagrams, or more than about 12 nodes | Write Mermaid source instead; ASCII cannot be aligned reliably at that size. |

Never hand-pad a generated diagram afterwards. If it needs a change, change the payload.

## 2. Generate

```sh
echo '{"headers":["Name","Role"],"rows":[["Ada","Engineer"]]}' \
  | python3 "${CLAUDE_SKILL_DIR}/scripts/asciid.py" gen table
```

Payloads, one per shape:

- `table`: `{"headers": [...], "rows": [[...], ...]}`
- `flow`: `{"steps": ["Parse", "Check"]}`
- `tree`: `{"node": {"label": "repo", "children": [{"label": "src"}]}}`
- `bar`: `{"pairs": [["parse", 12], ["check", 30]], "width": 20}`
- `arch`: `{"layers": [{"name": "Client", "components": ["Web", "CLI"]}]}`
- `seq`: `{"participants": ["User", "API"], "messages": [{"from": "User", "to": "API", "label": "request"}]}`

Add `--style light|heavy|double|rounded|ascii` (default `light`). Examples of each shape are in
`references/patterns.md`.

## 3. Check

```sh
python3 "${CLAUDE_SKILL_DIR}/scripts/asciid.py" check notes.md
python3 "${CLAUDE_SKILL_DIR}/scripts/asciid.py" check - < draft.txt   # stdin
```

Output lines read `path:line:col: severity: [rule] message`, with a suggestion where there is
one. Columns are display cells, not characters. Exit 0 means no errors (warnings alone still exit 0),
1 means errors (or warnings, with `--strict`), 2 means a usage or I/O problem. Useful flags: `--format json`, `--max-width N`, `--strict`
(warnings fail too), `--plain` (treat the whole input as one diagram), `--ambiguous-wide`
(for terminals that draw East Asian ambiguous characters two cells wide).
`asciid width "text"` prints the cell width of each line.

To skip a block, put `<!-- ascii-diagrams-disable: rule,rule -->` on the line before its fence.

The checks: `connect` (every line arm meets a partner; no dangling corner), `box` (a box
closes), `kink` (an off-by-one bend), `arrowhead` (the arrow lands on its box), `table` (equal
row width), `seam` (a vertical with nothing above or below), plus warnings `width`, `unstable`
and `ambiguous`.

## 4. Rules for drawing by hand

1. Pick one glyph set per diagram, named by use: light for the default, heavy for emphasis,
   double for a title or outer frame, rounded for soft grouping, ASCII for portable text.
   Mixing needs the junction glyphs in `references/glyphs.md`.
2. Keep to 76 cells in a terminal, 72 where the text reflows. The checker warns above 80.
3. Safe inside a frame: ASCII, box drawing, blocks, and CJK. Avoid emoji and ambiguous-width
   symbols (`※ ° ± × ★ ● ○`) in a framed line, and never put one left of a border on the same
   row. `references/widths.md` has the table.
4. One arrow style per diagram. Arrowheads must touch the box they point at.
5. Label things with short nouns. Put long text beside the diagram, not in it.
6. Use the closed status words `OK`, `WARN`, `FAIL`, `SKIP` rather than inventing marks.

Use the `+-|` set (`--style ascii`) for GitHub comments, CI logs, `NO_COLOR` output, mail and
anywhere the font is unknown. See `references/portable.md`.

## 5. The loop

1. Choose the route (section 1).
2. Generate, or draw.
3. Run `check`. Read every finding; fix the diagram, not the checker.
4. Repeat until exit 0, then paste the diagram.

## 6. Honest ceiling

The checker proves lines connect and widths agree under the Unicode tables of the running
Python. It cannot know your terminal's font, it cannot tell whether a diagram is clear, and
newer emoji are reported as `unstable` rather than measured. A clean exit means the geometry
is consistent, not that the picture is good. Read the diagram once as a reader would.

## References

- `references/glyphs.md`: box sets, arms, junctions, arrows, blocks.
- `references/widths.md`: cell widths and which characters may sit where.
- `references/patterns.md`: which diagram for which question, with examples; anti-patterns.
- `references/portable.md`: the `+-|` fallback.
