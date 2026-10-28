# Glyph reference

Every glyph is one cell wide in the box drawing (U+2500 to U+257F) and block (U+2580 to U+259F)
ranges. The checker treats each glyph as having arms (up, down, left, right) and requires that
every arm meets a partner.

## Sets

Name a set by use, not by look.

| Set | Use | Corners | Lines |
|---|---|---|---|
| light (default) | ordinary boxes, tables, trees | `┌ ┐ └ ┘` | `─ │` |
| heavy | emphasis, the thing to look at first | `┏ ┓ ┗ ┛` | `━ ┃` |
| double | a title, an outer frame | `╔ ╗ ╚ ╝` | `═ ║` |
| rounded | soft grouping, optional parts | `╭ ╮ ╰ ╯` | `─ │` |
| ascii | portable text | `+` | `- =` and `|` |

Generated examples:

```text
┌───┐  ┏━━━┓  ╔═══╗  ╭───╮  +---+
│ A │  ┃ A ┃  ║ A ║  │ A │  | A |
└───┘  ┗━━━┛  ╚═══╝  ╰───╯  +---+
```

## Junctions

| Meaning | Light | Heavy | Double |
|---|---|---|---|
| tee, branch right | `├` | `┣` | `╠` |
| tee, branch left | `┤` | `┫` | `╣` |
| tee, branch down | `┬` | `┳` | `╦` |
| tee, branch up | `┴` | `┻` | `╩` |
| cross | `┼` | `╋` | `╬` |

Mixed junctions join a double line to a single line. A double vertical meeting a single
horizontal uses `╞ ╟ ╡ ╢`: `╞` single line leaves to the right, `╟` double vertical with a
single branch right. For horizontal doubles, `╤ ╧ ╪` pair with single verticals, and `╥ ╨ ╫` do
the reverse. Light and heavy mix with `┝ ┞ ┟ ┠ ┡ ┢` and their relatives; use them only when
the weight change carries meaning.

A double frame around light boxes is legitimate and the checker accepts it:

```text
╔═════════════════╗
║  ┌───┐   ┌───┐  ║
║  │ A │   │ B │  ║
║  └───┘   └───┘  ║
╚═════════════════╝
```

## Rounded corners

Rounded corners are corners only. A rounded box has light lines and `╭ ╮ ╰ ╯` corners. Do not
mix rounded and square corners in one box.

## Line ends and half lines

`╴ ╵ ╶ ╷` are half lines (one arm). Use them for a line that ends in open space. Dashed lines
`┄ ┆ ╌ ╎` are light lines with the same arms; they read as "optional" or "async" but do not
change the checks.

## Arrows

| Direction | Heads |
|---|---|
| right | `►` `▶` `→` |
| left | `◄` `◀` `←` |
| down | `▼` `↓` |
| up | `▲` `↑` |

`v ^ > <` count as arrowheads only when they sit at the end of a line. Pick one family per
diagram; the generators use the triangle heads (`▼ ► ◄ ▲`) in Unicode styles and `v ^ > <` in
the ascii style. An arrowhead belongs directly against the box edge it points at, inside the
span of that edge.

```text
┌───────┐        ┌───────┐
│ Build ├───────►│ Test  │
└───────┘        └───────┘
```

## Blocks and shades

Full block `█`, shades `░ ▒ ▓`, partial blocks `▀ ▄ ▌ ▐` and the eighths `▁ ▂ ▃ ▄ ▅ ▆ ▇` are for
bar charts and sparklines. The `bar` generator uses `█`. Do not put a block inside a frame on
a row with text; shade widths vary by font.

```text
parse ████████ 12
check ████████████████████ 30
write █████ 7
```

## Status words

Prefer plain words (`OK`, `WARN`, `FAIL`, `SKIP`) over symbols. If a symbol is wanted, use one
that is not ambiguous in width: `✓` and `✗` are common but ambiguous in some fonts, so keep
them out of the column left of a border.
