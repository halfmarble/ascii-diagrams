# Cell widths

A terminal places text on a grid of cells. The checker and the generators count cells, never
characters or bytes.

## Policy

| Character | Cells |
|---|---|
| ASCII printable | 1 |
| box drawing, blocks (U+2500 to U+259F) | 1, always |
| East Asian Wide or Fullwidth (CJK, kana, hangul, fullwidth forms) | 2 |
| combining marks, zero width joiner, variation selectors, controls | 0 |
| emoji presented as emoji (variation selector 16, ZWJ sequences, flags) | 2, but unstable |
| East Asian Ambiguous (`° ± × ※ ★ ● ○ ·`) | 1, or 2 with `--ambiguous-wide` |
| anything else | 1 |

"Unstable" means the answer depends on the terminal, the font or the Unicode version of the
running Python. The checker reports `unstable` for these, and for characters newer than its own
Unicode tables. Python 3.9 ships Unicode 13; Python 3.14 ships Unicode 16, so a recent emoji
can measure differently between the two.

## Where each kind may sit

Inside a frame, the characters to the left of a border on the same row decide where that border
lands. So:

- Safe anywhere: ASCII, box drawing, blocks, CJK ideographs, kana, hangul.
- Allowed in a label, never left of a border on its row: ambiguous-width symbols.
- Avoid in a frame: emoji, flags, ZWJ sequences, characters with combining marks. The checker
  warns (`unstable`).
- If you need an emoji, put it outside the frame, or in a line with no border on it.

## CJK

Pad by cells, not characters. A two-character CJK word is four cells; padding it as if it were
two puts the border two columns short. The generators do this for you:

```text
┌──────┬──────────┐
│ Name │ Role     │
├──────┼──────────┤
│ Ada  │ Engineer │
│ 小林 │ Designer │
└──────┴──────────┘
```

Measure any line with `asciid width "小林 Designer"`; each row of output gives characters and cells.

## Budget

76 cells wide in a terminal, 72 where the text reflows (chat, Markdown preview). The checker's
`width` warning triggers above 80 by default; change it with `--max-width`.

## Checking your own terminal

If a diagram looks wrong on screen but checks clean, the font draws some character at a width
the tables do not expect. Try `--ambiguous-wide`, or replace the character.
