"""Tests for asciidiagrams.checks and asciidiagrams.report."""
import json
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "ascii-diagrams", "scripts"))

from asciidiagrams import report
from asciidiagrams.blocks import Block
from asciidiagrams.checks import ALL_RULES, DEFAULT_RULES, Finding, check_block, check_text


def found(text, kind="plain", **kw):
    return ["%s@%d:%d" % (f.rule, f.line, f.col) for f in check_text(text, "t", kind, **kw)]


def rules_of(text, **kw):
    return sorted({f.rule for f in check_text(text, "t", "plain", **kw)})


GOOD_BOX = """\
┌──────┐
│ box  │
└──────┘
"""


class Connect(unittest.TestCase):
    def test_clean_box(self):
        self.assertEqual(found(GOOD_BOX), [])

    def test_dangling_corner_into_space(self):
        text = "┌──────┐\n│ box  │\n└      ┘\n"
        self.assertEqual(found(text), ["connect@3:1", "box@3:2", "connect@3:8"])

    def test_corner_arm_into_text_is_dangling(self):
        text = "┌──────┐\n│ box  │\n└x     ┘\n"
        self.assertIn("connect@3:8", found(text))

    def test_line_end_into_space_is_allowed(self):
        self.assertEqual(found("│\n│\n│\n"), [])

    def test_tee_stem_into_space_is_allowed(self):
        text = "──┬──\n"
        self.assertEqual(found(text), [])

    def test_cross_must_connect_all_arms(self):
        text = "  │\n──┼──\n"
        self.assertIn("connect@2:3", found(text))

    def test_vertical_over_horizontal_is_a_mismatch(self):
        text = "   │\n┌──────┐\n│ box  │\n└──────┘\n"
        self.assertIn("connect@1:4", found(text))

    def test_arrowheads_end_arms(self):
        text = "──►\n"
        self.assertEqual([f for f in found(text) if f.startswith("connect")], [])
        text = "──┬──\n  │\n  ▼\n"
        self.assertEqual([f for f in found(text) if f.startswith("connect")], [])

    def test_ascii_arrow_next_to_line(self):
        self.assertEqual(found("──┐\n  │\n  v\n┌─┴─┐\n│   │\n└───┘\n"), [])

    def test_mixed_single_double_junctions(self):
        text = "╒═══╤═══╕\n│ a │ b │\n╘═══╧═══╛\n"
        self.assertEqual(found(text), [])

    def test_heavy_rounded_dashed_sets(self):
        for box in ("┏━━┓\n┃  ┃\n┗━━┛\n", "╭──╮\n│  │\n╰──╯\n", "┌╌╌┐\n┆  ┆\n└╌╌┘\n"):
            self.assertEqual(found(box), [], box)

    def test_one_finding_per_glyph_lists_both_arms(self):
        text = "x\n ┐\nx\n"
        f = check_text("┌─┐\n \n", "t", "plain")
        self.assertTrue(any("down arm" in x.message for x in f))
        del text


class Box(unittest.TestCase):
    def test_open_right_side(self):
        text = "┌──────┐\n│ box   │\n│ x    │\n└──────┘\n"
        self.assertIn("box@2:8", found(text))

    def test_missing_top_right_corner(self):
        text = "┌───────\n│ box  │\n│      │\n└──────┘\n"
        self.assertIn("box@1:9", found(text))

    def test_open_bottom(self):
        text = "┌──────┐\n│ box  │\n└──────  \n"
        self.assertIn("box@3:8", found(text))

    def test_connector_bend_is_not_a_box(self):
        text = "┌────┐\n│ in │\n└─┬──┘\n  │\n  └───┐\n      │\n      ▼\n"
        self.assertEqual([f for f in found(text) if f.startswith("box")], [])

    def test_label_in_border(self):
        text = "┌─ Title ──┐\n│ body     │\n└──────────┘\n"
        self.assertEqual(found(text), [])

    def test_gap_without_text_in_border_opens(self):
        text = "┌───    ───┐\n│          │\n└──────────┘\n"
        self.assertTrue(any(f.startswith("box@1:5") for f in found(text)))

    def test_ascii_box_open_side(self):
        text = "+------+\n| box   |\n| x    |\n+------+\n"
        self.assertTrue(any(f.startswith("box@") for f in found(text)))

    def test_ascii_box_right_side_one_column_right(self):
        self.assertIn("box@2:9", found("+-------+\n| Alpha  |\n+-------+\n"))

    def test_ascii_two_boxes_on_a_row(self):
        text = "+---+   +---+\n| a |   | b  |\n+---+   +---+\n"
        self.assertEqual([f for f in found(text) if f.startswith("box")], ["box@2:13"])

    def test_ascii_prose_and_file_tree_are_not_boxes(self):
        text = "+-- a\n|   +-- b\n+-- c\n\na + b --flags | x\n\n+---+\n| a |\n+---+\n"
        self.assertEqual(found(text), [])

    def test_ascii_lifeline_and_divider_junctions_are_not_corners(self):
        life = "+-----+\n| One |\n+--+--+\n   |\n   |\n"
        self.assertEqual(found(life), [])
        layered = "+---------+\n| Top     |\n+----+----+\n| a  | b  |\n+----+----+\n"
        self.assertEqual(found(layered), [])

    def test_ascii_box_clean(self):
        self.assertEqual(found("+------+\n| box  |\n+------+\n"), [])

    def test_nested_boxes(self):
        text = "┌────────┐\n│ ┌────┐ │\n│ │ in │ │\n│ └────┘ │\n└────────┘\n"
        self.assertEqual(found(text), [])

    def test_balanced_corner_counts_still_fail(self):
        text = "┌──────┐   ┌──────┐\n│ one  │   │ two  │\n└──────     ──────┘\n"
        got = found(text)
        self.assertIn("box@3:8", got)
        self.assertIn("box@3:12", got)


class KinkArrowSeam(unittest.TestCase):
    def test_kink(self):
        text = "┌──┬───┐\n│  │   │\n└──┴───┘\n   │\n    │\n ┌──┴───┐\n │ next │\n └──────┘\n"
        self.assertIn("kink@5:5", found(text))

    def test_junction_justifies_a_shift(self):
        text = "  │\n  └──┐\n     │\n"
        self.assertNotIn("kink", rules_of(text))

    def test_arrowhead_misses_box(self):
        text = "              ▼\n ┌──────────┐\n │ target   │\n └──────────┘\n"
        self.assertEqual(found(text), ["arrowhead@1:15"])

    def test_arrowhead_up_misses_box(self):
        text = " ┌──────────┐\n │ source   │\n └──────────┘\n              ▲\n"
        self.assertEqual(found(text), ["arrowhead@4:15"])

    def test_arrowhead_inside_span_is_fine(self):
        text = "     │\n     ▼\n ┌──────────┐\n │ target   │\n └──────────┘\n"
        self.assertEqual(found(text), [])

    def test_arrowhead_with_no_box_below_is_ignored(self):
        self.assertEqual(found("  │\n  ▼\n target\n"), [])

    def test_seam_single_shifted_row(self):
        text = "┌──────┐\n│ ok   │\n│ bad │\n│ ok   │\n└──────┘\n"
        self.assertIn("seam@3:7", found(text))

    def test_two_shifted_rows_anchor_each_other(self):
        text = "┌──────┐\n│ a     │\n│ b     │\n└──────┘\n"
        got = found(text)
        self.assertFalse(any(f.startswith("seam") for f in got))
        self.assertTrue(any(f.startswith("connect") for f in got))
        self.assertTrue(any(f.startswith("box") for f in got))


class Table(unittest.TestCase):
    CJK = (
        "┌────────┬──────┐\n"
        "│ 名前   │ 値   │\n"
        "├────────┼──────┤\n"
        "│ 速度   │ 42   │\n"
        "└────────┴──────┘\n"
    )

    def test_cjk_table_aligned_by_cells(self):
        self.assertEqual(found(self.CJK), [])

    def test_cjk_row_padded_by_characters(self):
        bad = self.CJK.replace("│ 速度   │", "│ 速度     │")
        got = found(bad)
        self.assertIn("table@4:19", got)

    def test_ascii_table_misaligned(self):
        text = "+----------+\n| name     |\n| other     |\n+----------+\n"
        self.assertIn("table@3:13", found(text))

    def test_markdown_pipe_table_is_not_checked(self):
        text = "| a | b |\n|---|---|\n| 1111 | 2 |\n"
        self.assertEqual(found(text), [])
        self.assertEqual(found("```text\n" + text + "```\n", "markdown"), [])

    def test_stacked_tables_of_different_widths(self):
        text = "┌────┐\n│ a  │\n└────┘\n┌──────────┐\n│ b        │\n└──────────┘\n"
        self.assertEqual(found(text), [])

    def test_ambiguous_wide_changes_cells(self):
        text = "┌───────┐\n│ 5 × 3 │\n│ 5 + 3 │\n└───────┘\n"
        self.assertIn("table", [x.split("@")[0] for x in found(text, ambiguous_wide=True)])
        self.assertNotIn("table", [x.split("@")[0] for x in found(text)])


class WidthAndStability(unittest.TestCase):
    def test_exactly_at_the_limit(self):
        line = "┌" + "─" * 78 + "┐"
        text = line + "\n│" + " " * 78 + "│\n└" + "─" * 78 + "┘\n"
        self.assertEqual(found(text), [])

    def test_over_the_limit(self):
        line = "┌" + "─" * 79 + "┐"
        text = line + "\n│" + " " * 79 + "│\n└" + "─" * 79 + "┘\n"
        self.assertEqual(found(text), ["width@1:81", "width@2:81", "width@3:81"])

    def test_limit_counts_cells_not_characters(self):
        text = GOOD_BOX + "中" * 21 + "\n"
        self.assertEqual(found(text, max_width=40), ["width@4:41"])
        self.assertEqual(found(text, max_width=42), [])

    def test_emoji_left_of_frame_warns(self):
        text = "┌────────┐\n│ ✅ ok  │\n└────────┘\n"
        self.assertEqual(found(text), ["unstable@2:3"])

    def test_emoji_right_of_the_last_frame_glyph_is_ignored(self):
        text = "┌────────┐\n│ ok     │ ✅\n└────────┘\n"
        self.assertEqual(found(text), [])

    def test_zwj_family_and_flag_are_two_cells(self):
        text = "┌────────┐\n│ 👨‍👩‍👧 x   │\n│ 🇯🇵 y   │\n└────────┘\n"
        f = check_text(text, "t", "plain")
        self.assertEqual([(x.rule, x.severity) for x in f], [("unstable", "warning")] * 2)
        self.assertTrue(all("2 cells" in x.message for x in f))

    def test_ambiguous_is_info(self):
        f = check_text("┌───────┐\n│ 5 × 3 │\n└───────┘\n", "t", "plain")
        self.assertEqual([(x.rule, x.severity) for x in f], [("ambiguous", "info")])

    def test_combining_mark_does_not_shift(self):
        text = "┌────┐\n│ é  │\n└────┘\n".replace("é", "é")
        self.assertEqual(found(text), [])


class Styles(unittest.TestCase):
    MIXED = "┌──┐\n│  │\n└┬─┘\n ▼\n╔══╗\n║  ║\n╚══╝\n"

    def test_off_by_default(self):
        self.assertEqual(rules_of(self.MIXED), [])

    def test_mixed_set_opt_in(self):
        self.assertEqual(rules_of(self.MIXED, rules=ALL_RULES), ["mixed-set"])

    def test_mixed_arrows_opt_in(self):
        text = "┌┬─┐\n│▼ │\n└┴─┘\n ↓\n"
        self.assertIn("mixed-arrows", rules_of(text, rules=ALL_RULES))

    def test_one_set_is_fine(self):
        self.assertEqual(rules_of(GOOD_BOX, rules=ALL_RULES), [])

    def test_default_rules_exclude_the_style_rules(self):
        self.assertEqual(ALL_RULES - DEFAULT_RULES, {"mixed-set", "mixed-arrows"})


class Trees(unittest.TestCase):
    TREE = "root/\n├── a\n│   └── b\n└── c\n"

    def test_tree_skips_connect_and_box(self):
        self.assertEqual(found(self.TREE), [])

    def test_heavy_double_and_rounded_trees(self):
        for tree in ("r/\n┣━━ a\n┃   ┗━━ b\n┗━━ c\n", "r/\n╠══ a\n║   ╚══ b\n╚══ c\n",
                     "r/\n├── a\n│   ╰── b\n╰── c\n"):
            self.assertEqual(found(tree), [], tree)

    def test_tree_still_gets_width(self):
        text = self.TREE + "├── " + "x" * 90 + "\n└── y\n"
        self.assertEqual(rules_of(text), ["width"])

    def test_broken_bottom_border_is_not_taken_for_a_tree(self):
        text = "┌──────┐\n│ box  │\n│      │\n└──────  \n"
        self.assertIn("box", rules_of(text))


class Disable(unittest.TestCase):
    BAD = "┌──────┐\n│ box   │\n└──────┘\n"

    def test_disabled_rule_is_dropped(self):
        block = Block("t", 1, self.BAD.split("\n")[:-1], "", {"seam", "table"})
        rules = {f.rule for f in check_block(block)}
        self.assertNotIn("seam", rules)
        self.assertNotIn("table", rules)
        self.assertIn("box", rules)

    def test_all_disables_everything(self):
        block = Block("t", 1, self.BAD.split("\n")[:-1], "", {"all"})
        self.assertEqual(check_block(block), [])

    def test_directive_in_markdown(self):
        md = "<!-- ascii-diagrams-disable: all -->\n```text\n" + self.BAD + "```\n"
        self.assertEqual(found(md, "markdown"), [])
        self.assertNotEqual(found("```text\n" + self.BAD + "```\n", "markdown"), [])

    def test_rules_argument_limits_the_run(self):
        block = Block("t", 1, self.BAD.split("\n")[:-1])
        self.assertEqual({f.rule for f in check_block(block, rules={"box"})}, {"box"})


class Lines(unittest.TestCase):
    def test_markdown_line_numbers_are_file_lines(self):
        md = "title\n\n```text\n┌──────┐\n│ box   │\n└──────┘\n```\n"
        self.assertIn("box@5:8", found(md, "markdown"))

    def test_columns_are_display_columns(self):
        text = "┌──────┐\n│ 中   │\n│ 中中 │\n└──────┘\n"
        self.assertEqual(found(text), [])
        bad = "┌──────┐\n│ 中中  │\n│ 中中 │\n└──────┘\n"
        self.assertIn("box@2:8", found(bad))

    def test_findings_are_sorted(self):
        text = "┌──────┐\n│ box   │\n│ x    │\n└──────┘\n"
        fs = check_text(text, "t", "plain")
        self.assertEqual(fs, sorted(fs, key=lambda f: (f.line, f.col, f.rule)))

    def test_text_without_diagrams(self):
        self.assertEqual(found("hello\nworld\n"), [])


class Report(unittest.TestCase):
    F1 = Finding(3, 8, "error", "box", "box opens", "close it")
    F2 = Finding(5, 2, "warning", "width", "too wide")
    F3 = Finding(6, 1, "info", "ambiguous", "ambiguous")

    def test_text_format(self):
        out = report.format_text([("a.md", [self.F1, self.F2])])
        self.assertEqual(out.split("\n"), [
            "a.md:3:8: error: [box] box opens",
            "  suggestion: close it",
            "a.md:5:2: warning: [width] too wide",
        ])

    def test_json_contract(self):
        obj = json.loads(report.format_json([("a.md", [self.F1, self.F2, self.F3]), ("b.md", [])]))
        self.assertEqual(obj["version"], 1)
        self.assertEqual(obj["counts"], {"error": 1, "warning": 1, "info": 1})
        self.assertEqual([f["path"] for f in obj["files"]], ["a.md", "b.md"])
        self.assertEqual(obj["files"][0]["findings"][0], {
            "line": 3, "col": 8, "severity": "error", "rule": "box",
            "message": "box opens", "suggestion": "close it"})
        self.assertIsNone(obj["files"][0]["findings"][1]["suggestion"])
        self.assertEqual(obj["files"][1]["findings"], [])

    def test_counts_and_summary(self):
        res = [("a", [self.F1]), ("b", [self.F2, self.F3])]
        self.assertEqual(report.counts(res), {"error": 1, "warning": 1, "info": 1})
        self.assertEqual(report.summary(res), "1 errors, 1 warnings, 1 info in 2 files")

    def test_empty(self):
        self.assertEqual(report.format_text([("a", [])]), "")
        self.assertEqual(report.counts([]), {"error": 0, "warning": 0, "info": 0})


if __name__ == "__main__":
    unittest.main()
