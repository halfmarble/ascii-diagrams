"""Tests for asciidiagrams.glyphs."""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "ascii-diagrams", "scripts"))

import unicodedata

from asciidiagrams import glyphs
from asciidiagrams.glyphs import ARMS, ARROWS, ASCII_ARROWS, SETS


class Arms(unittest.TestCase):
    def test_count(self):
        self.assertGreaterEqual(len(ARMS), 120)

    def test_light_corners(self):
        self.assertEqual(ARMS["┌"], frozenset("dr"))
        self.assertEqual(ARMS["┐"], frozenset("dl"))
        self.assertEqual(ARMS["└"], frozenset("ur"))
        self.assertEqual(ARMS["┘"], frozenset("ul"))

    def test_lines(self):
        self.assertEqual(ARMS["─"], frozenset("lr"))
        self.assertEqual(ARMS["│"], frozenset("ud"))

    def test_tees_and_cross(self):
        self.assertEqual(ARMS["├"], frozenset("udr"))
        self.assertEqual(ARMS["┤"], frozenset("udl"))
        self.assertEqual(ARMS["┬"], frozenset("dlr"))
        self.assertEqual(ARMS["┴"], frozenset("ulr"))
        self.assertEqual(ARMS["┼"], frozenset("udlr"))

    def test_heavy_double_rounded(self):
        self.assertEqual(ARMS["┏"], frozenset("dr"))
        self.assertEqual(ARMS["╔"], frozenset("dr"))
        self.assertEqual(ARMS["╭"], frozenset("dr"))
        self.assertEqual(ARMS["╬"], frozenset("udlr"))

    def test_dashed(self):
        self.assertEqual(ARMS["┄"], frozenset("lr"))
        self.assertEqual(ARMS["╎"], frozenset("ud"))

    def test_mixed_weights(self):
        self.assertEqual(ARMS["┍"], frozenset("dr"))  # down light, right heavy
        self.assertEqual(ARMS["╞"], frozenset("udr"))  # vertical single, right double
        self.assertEqual(ARMS["╪"], frozenset("udlr"))

    def test_half_lines(self):
        self.assertEqual(ARMS["╴"], frozenset("l"))
        self.assertEqual(ARMS["╻"], frozenset("d"))
        self.assertEqual(ARMS["╼"], frozenset("lr"))

    def test_ascii(self):
        self.assertEqual(ARMS["-"], frozenset("lr"))
        self.assertEqual(ARMS["="], frozenset("lr"))
        self.assertEqual(ARMS["|"], frozenset("ud"))
        self.assertEqual(ARMS["+"], frozenset("udlr"))

    def test_diagonals_excluded(self):
        for c in "╱╲╳":
            self.assertNotIn(c, ARMS)

    def test_every_box_glyph_but_diagonals_covered(self):
        missing = [chr(c) for c in range(0x2500, 0x2580)
                   if chr(c) not in ARMS and "DIAGONAL" not in unicodedata.name(chr(c))]
        self.assertEqual(missing, [])

    def test_values_are_frozensets_of_udlr(self):
        for ch, arms in ARMS.items():
            self.assertIsInstance(arms, frozenset)
            self.assertTrue(arms and arms <= frozenset("udlr"), ch)


class Arrows(unittest.TestCase):
    def test_directions(self):
        self.assertEqual(ARROWS["▼"], "d")
        self.assertEqual(ARROWS["▲"], "u")
        self.assertEqual(ARROWS["►"], "r")
        self.assertEqual(ARROWS["◄"], "l")
        self.assertEqual(ARROWS["→"], "r")
        self.assertEqual(ARROWS["↓"], "d")

    def test_ascii_heads_kept_apart(self):
        for c in "v^><":
            self.assertNotIn(c, ARROWS)
            self.assertIn(c, ASCII_ARROWS)


class Sets(unittest.TestCase):
    def test_names(self):
        self.assertEqual(set(SETS), {"light", "heavy", "double", "rounded", "ascii"})

    def test_same_keys(self):
        keys = set(SETS["light"])
        for name, s in SETS.items():
            self.assertEqual(set(s), keys, name)

    def test_arms_match_roles(self):
        want = {"h": "lr", "v": "ud", "tl": "dr", "tr": "dl", "bl": "ur",
                "br": "ul", "tee_r": "udr", "tee_l": "udl", "tee_d": "dlr",
                "tee_u": "ulr", "cross": "udlr"}
        for name, s in SETS.items():
            if name == "ascii":
                continue  # "+" carries all four arms in every role
            for role, arms in want.items():
                self.assertEqual(ARMS[s[role]], frozenset(arms), (name, role))

    def test_rounded_corners_differ_from_light(self):
        self.assertNotEqual(SETS["rounded"]["tl"], SETS["light"]["tl"])
        self.assertEqual(SETS["rounded"]["h"], SETS["light"]["h"])


class Groups(unittest.TestCase):
    def test_groups(self):
        self.assertIn("│", glyphs.VERTICALS)
        self.assertIn("═", glyphs.HORIZONTALS)
        self.assertIn("╭", glyphs.CORNERS)
        self.assertIn("╠", glyphs.TEES)

    def test_is_box_glyph(self):
        self.assertTrue(glyphs.is_box_glyph("─"))
        self.assertFalse(glyphs.is_box_glyph("-"))
        self.assertFalse(glyphs.is_box_glyph("ab"))


if __name__ == "__main__":
    unittest.main()
