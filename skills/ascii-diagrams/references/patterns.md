# Diagram patterns

## Which diagram for which question

| The reader asks | Use | Route |
|---|---|---|
| What are the fields or options? | table | `gen table` |
| What happens in order? | flow | `gen flow` |
| What contains what? | tree | `gen tree` |
| How big is each? | bar | `gen bar` |
| What are the layers? | arch | `gen arch` |
| Who talks to whom, when? | sequence | `gen seq` |
| Side-by-side comparison, annotated sketch (no generator covers it) | hand-drawn boxes | draw, then `check` |
| Classes, entities, states, schedules | Mermaid source | no ASCII |

If one diagram answers two questions, make two diagrams.

## Generated examples

Every example below came from `asciid gen`. Generate first; draw by hand only for shapes the
generators do not cover, and check what you draw.

Table (`gen table`):

```text
┌──────┬──────────┐
│ Name │ Role     │
├──────┼──────────┤
│ Ada  │ Engineer │
│ 小林 │ Designer │
└──────┴──────────┘
```

Flow (`gen flow`):

```text
┌───────┐
│ Parse │
└───┬───┘
    │
    ▼
┌───────┐
│ Check │
└───┬───┘
    │
    ▼
┌───────┐
│ Write │
└───────┘
```

Tree (`gen tree`):

```text
repo
├─ src
│  ├─ main.py
│  └─ util.py
└─ README.md
```

Bar chart (`gen bar`):

```text
parse ████████ 12
check ████████████████████ 30
write █████ 7
```

Layered architecture (`gen arch`):

```text
┌──────────────────────┐
│        Client        │
├──────────┬───────────┤
│ Web      │ CLI       │
└──────────┴───────────┘
┌──────────────────────┐
│       Service        │
├─────┬────────┬───────┤
│ API │ Worker │ Queue │
└─────┴────────┴───────┘
```

Sequence (`gen seq`; the lifelines run unbroken and each arrow leaves a lifeline through a tee):

```text
┌──────┐   ┌─────┐   ┌────┐
│ User │   │ API │   │ DB │
└───┬──┘   └──┬──┘   └──┬─┘
    │         │         │
    │         │         │
    │ request │         │
    ├────────►│         │
    │         │  query  │
    │         ├────────►│
    │         │  rows   │
    │         │◄────────┤
    │  reply  │         │
    │◄────────┤         │
```

## Hand-drawn: side by side

When two boxes sit on one row, the rows must have the same cell width on both sides. Draw
the whole row, then check.

```text
┌───────────┐     ┌───────────┐
│  Before   │     │  After    │
├───────────┤     ├───────────┤
│ 3 steps   │     │ 1 step    │
└───────────┘     └───────────┘
```

A connector with a bend needs its corners to meet:

```text
┌───────┐
│ Input │
└───┬───┘
    │
    └────────┐
             ▼
        ┌────────┐
        │ Output │
        └────────┘
```

## Principles

- **Say one thing.** A diagram with a single message beats one with six.
- **Order carries meaning.** Flow runs top to bottom or left to right; do not mix.
- **Group by closeness.** Boxes near each other read as related; use space before using lines.
- **Align.** Shared edges and a common left margin make the structure visible.
- **Cut decoration.** Heavy borders everywhere, nested frames for their own sake and repeated
  fills add noise, not information.
- **Label the arrows that need it.** An unlabelled arrow means "then" or "calls"; if it means
  something else, say so.

## Anti-patterns

- **Spaghetti arrows.** Lines that cross three times. Reorder the nodes, or split the diagram.
- **Too many nodes.** Past about a dozen, switch to Mermaid or to a table.
- **Mixed arrow styles.** `→`, `►` and `-->` in one diagram.
- **Border drift.** A right edge one column off. Generate, or run `check`.
- **Emoji in a frame.** Its width depends on the terminal. Move it out.
- **Hand-padded CJK.** Padding by characters. Pad by cells, or generate.
- **Prose in boxes.** If a box holds a sentence, it is a paragraph.
- **A diagram nobody can reuse.** If the payload is gone, the next edit is by hand again.
  Keep the JSON payload next to the source when the diagram will change.
