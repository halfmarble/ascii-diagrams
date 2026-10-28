# ascii-diagrams

A Claude Code plugin that draws and checks text diagrams: boxes, tables, flows, trees,
architecture sketches. It exists because hand-drawn ASCII and Unicode boxes drift: a right
border lands one column off, a CJK label is padded by characters instead of cells, an emoji
shifts everything after it.

It has two parts:

- a **skill** (`skills/ascii-diagrams/`) that tells the model when to generate a diagram, when
  to draw one and verify it, and when to write Mermaid instead;
- a **mod** (`hooks/`) that checks Markdown and text files after a Write or Edit and reports
  findings back to the model, plus an `/ascii` command.

Both use one stdlib-only Python tool, `asciid.py` (Python 3.9 or later, no packages).

## Install

In Claude Code:

```text
/plugin install ascii-diagrams --marketplace halfmarble/ascii-diagrams
```

Answer `y` if it asks you to confirm. The scope question (user, project or local) is yours:
user scope makes it available in every project.

The mod needs `python3`. On macOS without the Command Line Tools, `/usr/bin/python3` is a stub
that opens an install dialog; the mod checks `xcode-select -p` first and stays off if the tools
are missing. Set the `python` option to point at another interpreter.

Options (declared in the plugin's `userConfig`):

| Option | Default | Meaning |
|---|---|---|
| `python` | empty (find `python3` on the PATH) | interpreter that runs `asciid.py` |
| `extensions` | `.md,.markdown,.txt` | file extensions the mod checks when written |
| `triggerCard` | on | the short card added to each session; set false to drop it |

Set them in Claude Code under `/plugin`, in the plugin's configure screen, or at install time:

```text
claude plugin install ascii-diagrams --marketplace halfmarble/ascii-diagrams --config python=/path/to/python3
```

`--config <key=value>` is repeatable.

### Skill only

Copy `skills/ascii-diagrams/` into `~/.claude/skills/`. You get the skill and the CLI but no
mod and no `/ascii` command. The skill's commands use `${CLAUDE_SKILL_DIR}`; that this expands
for a skill copied outside a plugin has not been measured, so if the script path does not
resolve, tell the model the folder the skill was copied to.

## Command line

```sh
S=skills/ascii-diagrams/scripts/asciid.py

python3 $S check README.md docs/            # files or directories (*.md *.markdown *.txt)
python3 $S check - < draft.txt              # stdin
python3 $S check notes.md --format json     # for tools
echo '{"headers":["Name","Role"],"rows":[["Ada","Engineer"]]}' | python3 $S gen table
python3 $S width "小林 Designer"             # cell width per line
```

`gen` shapes: `table`, `flow`, `tree`, `bar`, `arch`, `seq`, each with
`--style light|heavy|double|rounded|ascii`. Payload formats are in
`skills/ascii-diagrams/SKILL.md`.

`check` options: `--max-width N` (default 80), `--ambiguous-wide`, `--style` (also report mixed
sets and arrow styles), `--strict` (warnings fail), `--plain` (treat the input as one block).
Exit codes: 0 no errors (warnings alone exit 0 unless `--strict`), 1 errors (or warnings with
`--strict`), 2 usage or I/O error.

Findings read `path:line:col: severity: [rule] message`; columns count display cells. Rules:
`connect`, `box`, `kink`, `arrowhead`, `table`, `seam` (errors); `width`, `unstable` (warnings);
`ambiguous` (info).

To skip a block, put `<!-- ascii-diagrams-disable: rule,rule -->` on the line before its fence.

A small example, as the checker sees it:

```text
┌──────┬──────────┐
│ Name │ Role     │
├──────┼──────────┤
│ Ada  │ Engineer │
│ 小林 │ Designer │
└──────┴──────────┘
```

## Tests

```sh
python3 -m unittest discover -s tests -t .
```

## Limits

The checker verifies geometry and width under the Unicode tables of the Python that runs it.
It cannot see your terminal's font. Emoji and characters newer than those tables are reported
as `unstable` rather than measured.

## Credits and licence

MIT. The tool merges ideas and code from four MIT-licensed community projects; each is credited,
with its pinned commit and the files drawn on, in `THIRD_PARTY_NOTICES.md`.
