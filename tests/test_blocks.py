"""Tests for asciidiagrams.blocks."""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "ascii-diagrams", "scripts"))

from asciidiagrams.blocks import Block, extract, is_diagram, parse_disable, split_lines

BOX = ["┌───┐", "│ a │", "└───┘"]
BOX_TEXT = "\n".join(BOX)


def fenced(lang, body=BOX_TEXT, fence="```"):
    return "%s%s\n%s\n%s" % (fence, lang, body, fence)


class IsDiagram(unittest.TestCase):
    def test_three_box_glyphs(self):
        self.assertTrue(is_diagram(["┌─┐"]))

    def test_two_box_glyphs_is_not_enough(self):
        self.assertFalse(is_diagram(["┌─"]))

    def test_two_ascii_border_rows(self):
        self.assertTrue(is_diagram(["+---+", "| a |", "+---+"]))

    def test_one_ascii_border_row_is_not_enough(self):
        self.assertFalse(is_diagram(["+---+", "| a |"]))

    def test_two_boxes_on_a_row_are_a_diagram(self):
        self.assertTrue(is_diagram(["+---+   +---+", "| a |   | b |", "+---+   +---+"]))
        self.assertTrue(is_diagram(["+---+ --> +---+", "| a |     | b |", "+---+ --> +---+"]))

    def test_plus_runs_and_prose_are_not_borders(self):
        self.assertFalse(is_diagram(["+++ b/f", "+++", "a + b +", "+-- x"]))

    def test_pipe_table_is_not_a_diagram(self):
        self.assertFalse(is_diagram(["| a | b |", "|---|---|", "| 1 | 2 |"]))

    def test_code_language_skips_ascii_borders(self):
        self.assertFalse(is_diagram(["+---+", "| a |", "+---+"], "bash"))

    def test_code_language_with_box_glyphs_is_still_a_diagram(self):
        self.assertTrue(is_diagram(BOX, "bash"))


class Markdown(unittest.TestCase):
    def test_backtick_fence(self):
        blocks = extract("intro\n\n" + fenced("text"))
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].lines, BOX)
        self.assertEqual(blocks[0].lang, "text")

    def test_start_line_is_first_content_line(self):
        blocks = extract("a\nb\n" + fenced(""))
        self.assertEqual(blocks[0].start_line, 4)

    def test_tilde_fence(self):
        blocks = extract(fenced("", fence="~~~"))
        self.assertEqual(len(blocks), 1)

    def test_longer_fence_holds_a_shorter_one(self):
        body = BOX_TEXT + "\n```\nnot a close\n```"
        blocks = extract("````text\n" + body + "\n````")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(len(blocks[0].lines), len(BOX) + 3)

    def test_code_language_fence_skipped(self):
        text = "```bash\n+---+\n| a |\n+---+\n```"
        self.assertEqual(extract(text), [])

    def test_code_language_with_box_glyphs_checked(self):
        self.assertEqual(len(extract(fenced("python"))), 1)

    def test_text_txt_ascii_diagram_and_none_are_checked(self):
        for lang in ("text", "txt", "ascii", "diagram", ""):
            self.assertEqual(len(extract(fenced(lang))), 1, lang)

    def test_info_string_with_attributes(self):
        blocks = extract(fenced("text title=x"))
        self.assertEqual(blocks[0].lang, "text")

    def test_two_blocks(self):
        text = fenced("text") + "\n\nmid\n\n" + fenced("text")
        blocks = extract(text)
        self.assertEqual([b.start_line for b in blocks], [2, 10])

    def test_unclosed_fence_runs_to_the_end(self):
        blocks = extract("```text\n" + BOX_TEXT)
        self.assertEqual(blocks[0].lines, BOX)

    def test_indented_fence(self):
        text = "- item\n\n  ```text\n" + "\n".join("  " + ln for ln in BOX) + "\n  ```"
        self.assertEqual(len(extract(text)), 1)

    def test_disable_directive_on_previous_line(self):
        text = "<!-- ascii-diagrams-disable: seam, box -->\n" + fenced("text")
        self.assertEqual(extract(text)[0].disabled, {"seam", "box"})

    def test_disable_directive_two_lines_up_is_ignored(self):
        text = "<!-- ascii-diagrams-disable: seam -->\n\n" + fenced("text")
        self.assertEqual(extract(text)[0].disabled, set())

    def test_prose_without_diagram_has_no_blocks(self):
        self.assertEqual(extract("just\nsome words\n- a list\n"), [])

    def test_unfenced_box_run_is_a_block(self):
        self.assertEqual([b.start_line for b in extract("just\n" + BOX_TEXT)], [2])

    def test_crlf_lines(self):
        blocks = extract(fenced("text").replace("\n", "\r\n"))
        self.assertEqual(blocks[0].lines, BOX)

    def test_path_is_kept(self):
        self.assertEqual(extract(fenced("text"), path="x.md")[0].path, "x.md")

    def test_unknown_kind(self):
        with self.assertRaises(ValueError):
            extract("x", "html")


class Plain(unittest.TestCase):
    def test_whole_text_is_one_block(self):
        blocks = extract(BOX_TEXT, "plain")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].start_line, 1)
        self.assertEqual(blocks[0].lines, BOX)

    def test_text_without_a_diagram_has_no_block(self):
        self.assertEqual(extract("hello\nworld", "plain"), [])

    def test_disable_directive_anywhere(self):
        text = "<!-- ascii-diagrams-disable: width -->\n" + BOX_TEXT
        self.assertEqual(extract(text, "plain")[0].disabled, {"width"})


class Helpers(unittest.TestCase):
    def test_parse_disable(self):
        self.assertEqual(parse_disable("<!-- ascii-diagrams-disable: a,b -->"), {"a", "b"})
        self.assertEqual(parse_disable("nothing here"), set())

    def test_split_lines_only_on_newline(self):
        self.assertEqual(split_lines("a\r\nb\x0cc\n"), ["a", "b\x0cc", ""])

    def test_block_text(self):
        self.assertEqual(Block("p", 1, ["a", "b"]).text, "a\nb")


class Unfenced(unittest.TestCase):
    BOX = ["┌───────┐", "│ Alpha │", "└───────┘"]

    def test_bare_box_diagram_in_markdown(self):
        text = "Intro\n\n" + "\n".join(self.BOX) + "\n\nOutro\n"
        blocks = extract(text, "markdown")
        self.assertEqual([(b.start_line, b.lines) for b in blocks], [(3, self.BOX)])

    def test_indented_ascii_box_with_true_line_numbers(self):
        text = "Intro\n\n    +---+\n    | a |\n    +---+\n"
        blocks = extract(text, "markdown")
        self.assertEqual([(b.start_line, b.lines) for b in blocks], [(3, ["+---+", "| a |", "+---+"])])

    def test_pipe_table_and_html_comment_are_skipped(self):
        text = "| a | b |\n|---|---|\n| 1 | 2 |\n\n<!--\n" + "\n".join(self.BOX) + "\n-->\n"
        self.assertEqual(extract(text, "markdown"), [])

    def test_fenced_box_is_not_taken_twice(self):
        text = "```text\n" + "\n".join(self.BOX) + "\n```\n"
        self.assertEqual(len(extract(text, "markdown")), 1)

    def test_single_glyph_line_is_not_a_diagram(self):
        self.assertEqual(extract("a\n\n┌─┐ x\n\nb\n", "markdown"), [])


if __name__ == "__main__":
    unittest.main()
