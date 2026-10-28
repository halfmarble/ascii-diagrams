"""Tests for asciidiagrams.width."""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "ascii-diagrams", "scripts"))

from asciidiagrams import width
from asciidiagrams.width import cell_width, clusters, display_width, split_lines, stability


class DisplayWidth(unittest.TestCase):
    def test_ascii(self):
        self.assertEqual(display_width("abc123"), 6)

    def test_empty(self):
        self.assertEqual(display_width(""), 0)

    def test_cjk_is_two(self):
        self.assertEqual(display_width("中文"), 4)

    def test_kana_kanji(self):
        self.assertEqual(display_width("あア漢"), 6)

    def test_fullwidth_forms(self):
        self.assertEqual(display_width("　"), 2)
        self.assertEqual(display_width("Ａ"), 2)

    def test_box_drawing_is_one(self):
        self.assertEqual(display_width("┌─┐│└┘╔═╗"), 9)

    def test_blocks_are_one(self):
        self.assertEqual(display_width("█▓▒░▀▄"), 6)

    def test_control_is_zero(self):
        self.assertEqual(display_width("a\x00\x07b"), 2)

    def test_zero_width_space_and_bom(self):
        self.assertEqual(display_width("a​b﻿"), 2)

    def test_combining_mark_adds_nothing(self):
        self.assertEqual(display_width("é"), 1)

    def test_lone_combining_mark_is_zero(self):
        self.assertEqual(display_width("́"), 0)

    def test_ambiguous_default_one(self):
        self.assertEqual(display_width("±★"), 2)

    def test_ambiguous_wide_option(self):
        self.assertEqual(display_width("±★", ambiguous_wide=True), 4)

    def test_ambiguous_wide_leaves_box_drawing(self):
        self.assertEqual(display_width("─│", ambiguous_wide=True), 2)

    def test_emoji_is_two(self):
        self.assertEqual(display_width("\U0001f600"), 2)

    def test_zwj_family_is_two(self):
        self.assertEqual(display_width("\U0001f468‍\U0001f469‍\U0001f467"), 2)

    def test_flag_is_two(self):
        self.assertEqual(display_width("\U0001f1ef\U0001f1f5"), 2)

    def test_two_flags_are_four(self):
        self.assertEqual(display_width("\U0001f1ef\U0001f1f5\U0001f1fa\U0001f1f8"), 4)

    def test_vs16_cluster_is_two(self):
        self.assertEqual(display_width("❤️"), 2)

    def test_skin_tone_modifier_joins(self):
        self.assertEqual(display_width("\U0001f44d\U0001f3fd"), 2)

    def test_mixed_line(self):
        self.assertEqual(display_width("ab中c"), 5)


class Clusters(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(clusters("ab"), [("a", 1), ("b", 1)])

    def test_combining_joins_base(self):
        self.assertEqual(clusters("éx"), [("é", 1), ("x", 1)])

    def test_zwj_sequence_is_one_cluster(self):
        fam = "\U0001f468‍\U0001f469‍\U0001f467"
        self.assertEqual(clusters(fam + "a"), [(fam, 2), ("a", 1)])

    def test_flag_pair_is_one_cluster(self):
        jp = "\U0001f1ef\U0001f1f5"
        self.assertEqual(clusters(jp), [(jp, 2)])

    def test_cluster_text_round_trips(self):
        s = "a中❤️é\U0001f1ef\U0001f1f5\x07z"
        self.assertEqual("".join(c for c, _ in clusters(s)), s)

    def test_empty(self):
        self.assertEqual(clusters(""), [])


class CellWidth(unittest.TestCase):
    def test_single_cjk(self):
        self.assertEqual(cell_width("中"), 2)

    def test_empty_cluster(self):
        self.assertEqual(cell_width(""), 0)

    def test_ambiguous_flag(self):
        self.assertEqual(cell_width("±", ambiguous_wide=True), 2)
        self.assertEqual(cell_width("±"), 1)


class Stability(unittest.TestCase):
    def test_ascii_stable(self):
        self.assertEqual(stability("a"), "stable")

    def test_cjk_stable(self):
        self.assertEqual(stability("中"), "stable")

    def test_box_stable(self):
        self.assertEqual(stability("│"), "stable")

    def test_ambiguous(self):
        self.assertEqual(stability("±"), "ambiguous")

    def test_emoji_unstable(self):
        self.assertEqual(stability("\U0001f600"), "unstable")

    def test_zwj_unstable(self):
        self.assertEqual(stability("\U0001f468‍\U0001f469"), "unstable")

    def test_vs16_unstable(self):
        self.assertEqual(stability("❤️"), "unstable")

    def test_flag_unstable(self):
        self.assertEqual(stability("\U0001f1ef\U0001f1f5"), "unstable")

    def test_unassigned_unstable(self):
        # U+0378 is unassigned in every Unicode version
        self.assertEqual(stability("͸"), "unstable")


class SplitLines(unittest.TestCase):
    def test_empty_gives_one_line(self):
        self.assertEqual(split_lines(""), [""])

    def test_crlf_and_bare_cr(self):
        self.assertEqual(split_lines("a\r\nb\rc"), ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
