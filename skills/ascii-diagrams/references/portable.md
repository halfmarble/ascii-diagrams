# Portable diagrams

Use the `+-|` set when you cannot trust the viewer to draw box glyphs at one cell each:

- GitHub comments and issue bodies in some fonts
- CI logs and terminals with `NO_COLOR` or a limited locale
- email, code comments in files that must stay ASCII
- fonts you have not seen

## How

Generate with `--style ascii`:

```text
+-------+
| Build |
+-------+
    |
    v
+-------+
| Test  |
+-------+
```

```text
+----------+-------+
| Key      | Use   |
+----------+-------+
| default  | light |
| emphasis | heavy |
+----------+-------+
```

Trees use `|- ` and `` `- `` for branches. Arrowheads are `v ^ > <`.

## Hand drawing

- Corners and joints are `+`; horizontal runs `-` (or `=` for emphasis); vertical runs `|`.
- A `+` only counts as a joint when two or more line cells touch it, so a lone `+` in text is not
  mistaken for a corner.
- Keep CJK out of ASCII-only places; if you must, pad by cells.

A hand-drawn check:

```text
+-----+     +-----+
| One | --> | Two |
+-----+     +-----+
```

## Converting

To convert an existing Unicode diagram, regenerate it from its payload with `--style ascii`.
Do not search and replace glyphs; line ends and joints change.
