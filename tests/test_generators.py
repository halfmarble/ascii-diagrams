"""Tests for asciidiagrams.generators."""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "ascii-diagrams", "scripts"))

from asciidiagrams import generators
from asciidiagrams.generators import SHAPES, STYLES, render
from asciidiagrams.glyphs import ARMS, SETS
from asciidiagrams.width import display_width

LABELS = {
    "ascii": ["Receive", "Validate order", "Store", "Done"],
    "cjk": ["收到訂單", "驗證ユーザー", "庫存", "完成"],
    "mixed": ["API サービス", "DB", "ユーザー User", "Cache"],
}


def payload(shape, labels, style):
    a, b, c, d = labels
    p = {
        "table": {"headers": [a, b], "rows": [[c, d], [d + "\n" + c, a]]},
        "flow": {"steps": [a, b + "\n" + c, d]},
        "tree": {"node": {"label": a, "children": [
            {"label": b, "children": [{"label": c}]}, {"label": d}]}},
        "bar": {"pairs": [[a, 3], [b, 10], [c, 0]], "width": 12},
        "arch": {"layers": [{"name": a, "components": [b, c + "\n" + d, a]},
                            {"name": b, "components": [c]}]},
        "seq": {"participants": [a, b, c],
                "messages": [{"from": a, "to": c, "label": d + " " + b},
                             {"from": c, "to": b, "label": "ok"}]},
    }[shape]
    p["style"] = style
    return p


def cells(line):
    """One entry per display cell: a wide character is followed by a blank."""
    out = []
    for ch in line:
        out.append(ch)
        out.extend("" for _ in range(display_width(ch) - 1))
    return out


def frame_glyphs(style):
    st = set(SETS[style].values())
    if style == "ascii":
        st |= {"+", "-", "|"}
    return st


def framed_blocks(lines, style):
    """Runs of consecutive lines that start and end with a frame glyph."""
    fg = frame_glyphs(style)
    blocks, cur = [], []
    for ln in lines:
        if ln and ln[0] in fg and ln[-1] in fg:
            cur.append(ln)
        else:
            if cur:
                blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return blocks


class MatrixTest(unittest.TestCase):
    def test_shape_style_labels(self):
        rendered = 0
        framed = 0
        for shape in SHAPES:
            for style in STYLES:
                for name, labels in LABELS.items():
                    with self.subTest(shape=shape, style=style, labels=name):
                        out = render(shape, payload(shape, labels, style))
                        rendered += 1
                        self.assertTrue(out.strip())
                        self.assertNotIn("\r", out)
                        lines = out.split("\n")
                        if shape in ("table", "flow", "arch", "seq"):
                            blocks = framed_blocks(lines, style)
                            self.assertTrue(blocks)
                            for blk in blocks:
                                framed += 1
                                widths = {display_width(l) for l in blk}
                                self.assertEqual(len(widths), 1, "\n" + "\n".join(blk))
                        if shape == "seq":
                            # no trailing spaces: no line is wider than the participant header row
                            self.assertEqual(max(display_width(l) for l in lines), display_width(lines[0]), "\n" + out)
                        if style == "ascii" and name == "ascii":
                            self.assertTrue(out.isascii(), out)
        self.assertEqual(rendered, len(SHAPES) * len(STYLES) * len(LABELS))
        self.assertGreaterEqual(rendered, 90)
        self.assertGreater(framed, 0)


class ShapeTest(unittest.TestCase):
    def test_table_light_exact(self):
        out = render("table", {"headers": ["a", "bb"], "rows": [["ccc", "d"]]})
        self.assertEqual(out, "\n".join([
            "┌─────┬────┐", "│ a   │ bb │", "├─────┼────┤",
            "│ ccc │ d  │", "└─────┴────┘"]))

    def test_table_ascii_only_flag(self):
        out = render("table", {"headers": ["a"], "rows": [["b"]], "ascii_only": True})
        self.assertTrue(out.isascii())
        self.assertTrue(out.startswith("+---+"))

    def test_table_cjk_columns_align(self):
        out = render("table", {"headers": ["名前", "n"], "rows": [["ab", "x"]]})
        self.assertEqual(len({display_width(l) for l in out.split("\n")}), 1)

    def test_table_ragged_row_rejected(self):
        with self.assertRaises(ValueError):
            render("table", {"headers": ["a", "b"], "rows": [["x"]]})

    def test_flow_trunk_column(self):
        out = render("flow", {"steps": ["ab", "cdef"]}).split("\n")
        trunk = [l for l in out if l.strip() in ("│", "▼")]
        self.assertEqual(len(trunk), 2)
        self.assertEqual(len({l.index(l.strip()) for l in trunk}), 1)
        self.assertEqual(out[0], out[5])

    def test_tree_exact(self):
        out = render("tree", {"node": {"label": "r", "children": [
            {"label": "a", "children": [{"label": "b"}]}, {"label": "c"}]}})
        self.assertEqual(out, "r\n├─ a\n│  └─ b\n└─ c")

    def test_tree_ascii(self):
        out = render("tree", {"node": {"label": "r", "children": [{"label": "a"}]}, "style": "ascii"})
        self.assertTrue(out.isascii())

    def test_bar_scale_and_alignment(self):
        out = render("bar", {"pairs": [["日本", 5], ["x", 10]], "width": 10}).split("\n")
        self.assertEqual(out[0], "日本 █████ 5")
        self.assertEqual(out[1], "x    ██████████ 10")
        self.assertEqual(display_width(out[0].split("█")[0]), display_width(out[1].split("█")[0]))

    def test_bar_rejects_negative_and_breaks(self):
        with self.assertRaises(ValueError):
            render("bar", {"pairs": [["a", -1]]})
        with self.assertRaises(ValueError):
            render("bar", {"pairs": [["a\rb", 1]]})

    def test_arch_junctions(self):
        out = render("arch", {"layers": [{"name": "L", "components": ["a", "b"]}]}).split("\n")
        self.assertIn("┬", out[2])
        self.assertIn("┴", out[4])
        self.assertEqual(out[2].index("┬"), out[4].index("┴"))
        self.assertEqual(out[2].index("┬"), out[3].index("│", 1))

    def test_seq_arrowhead_beside_lifeline(self):
        out = render("seq", {"participants": ["A", "B", "C"],
                             "messages": [{"from": "A", "to": "C", "label": "go"}]}).split("\n")
        arrow = out[-1]
        life = out[3]
        self.assertEqual(arrow.index("►"), life.rindex("│") - 1)
        self.assertEqual(arrow[life.rindex("│")], "│")
        self.assertEqual(arrow.index("├"), life.index("│"))
        self.assertEqual(arrow[life.index("│", 1 + life.index("│"))], "┼")

    def test_seq_lifelines_continuous(self):
        for style in STYLES:
            for name, labels in LABELS.items():
                with self.subTest(style=style, labels=name):
                    lines = render("seq", payload("seq", labels, style)).split("\n")
                    st = SETS[style]
                    body = [cells(l) for l in lines[3:]]
                    cols = [i for i, ch in enumerate(body[0]) if ch == st["v"]]
                    self.assertEqual(len(cols), 3)
                    ok = {st["v"], st["tee_r"], st["tee_l"], st["cross"]}
                    for row in body:
                        for c in cols:
                            self.assertIn(row[c] if c < len(row) else " ", ok, "\n" + "\n".join(lines))

    def test_flow_junction_glyphs(self):
        for style in STYLES:
            for name, labels in LABELS.items():
                with self.subTest(style=style, labels=name):
                    out = render("flow", payload("flow", labels, style)).split("\n")
                    st = SETS[style]
                    # a bottom border is the line just above each trunk line, and the last line
                    bottoms = [out[i - 1] for i, l in enumerate(out) if l.strip() == st["v"]]
                    self.assertEqual(len(bottoms), 2)
                    trunk = [l.index(st["v"]) for l in out if l.strip() == st["v"]]
                    self.assertEqual([b[c] for b, c in zip(bottoms, trunk)], [st["tee_d"]] * 2)
                    if style != "ascii":
                        self.assertNotIn(st["tee_d"], out[-1])

    def test_no_trailing_whitespace(self):
        for shape in SHAPES:
            for style in STYLES:
                for name, labels in LABELS.items():
                    with self.subTest(shape=shape, style=style, labels=name):
                        for l in render(shape, payload(shape, labels, style)).split("\n"):
                            self.assertEqual(l, l.rstrip(), repr(l))

    def test_seq_leftward_and_ascii(self):
        out = render("seq", {"participants": ["A", "B"], "style": "ascii",
                             "messages": [{"from": "B", "to": "A", "label": "back"}]})
        self.assertTrue(out.isascii())
        self.assertIn("<", out.split("\n")[-1])

    def test_seq_wide_label_widens_gap(self):
        out = render("seq", {"participants": ["A", "B"],
                             "messages": [{"from": "A", "to": "B", "label": "a very long message label"}]})
        self.assertIn("a very long message label", out)

    def test_seq_self_message_rejected(self):
        with self.assertRaises(ValueError):
            render("seq", {"participants": ["A"], "messages": [{"from": "A", "to": "A", "label": "x"}]})

    def test_empty_inputs(self):
        self.assertEqual(render("flow", {"steps": []}), "")
        self.assertEqual(render("bar", {"pairs": []}), "")
        self.assertEqual(render("arch", {"layers": []}), "")
        self.assertEqual(render("seq", {"participants": [], "messages": []}), "")

    def test_unknown_shape_style_and_payload(self):
        with self.assertRaises(ValueError):
            render("pie", {})
        with self.assertRaises(ValueError):
            render("flow", {"steps": ["a"], "style": "neon"})
        with self.assertRaises(ValueError):
            render("flow", {})
        with self.assertRaises(ValueError):
            render("flow", [])

    def test_non_string_label_rejected(self):
        with self.assertRaises(ValueError):
            render("flow", {"steps": [1]})

    def test_glyphs_are_known_box_glyphs(self):
        for style in ("light", "heavy", "double", "rounded"):
            out = render("arch", payload("arch", LABELS["mixed"], style))
            for ch in out:
                if 0x2500 <= ord(ch) <= 0x257F:
                    self.assertIn(ch, ARMS)

    def test_exports(self):
        self.assertEqual(len(SHAPES), 6)
        self.assertEqual(len(STYLES), 5)
        self.assertTrue(hasattr(generators, "render"))


if __name__ == "__main__":
    unittest.main()
