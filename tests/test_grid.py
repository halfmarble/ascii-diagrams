"""Tests for asciidiagrams.grid."""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "ascii-diagrams", "scripts"))

from asciidiagrams.grid import Grid


class Cells(unittest.TestCase):
    def test_ascii_row(self):
        g = Grid(["abc"])
        self.assertEqual([g.at(0, c) for c in range(3)], ["a", "b", "c"])

    def test_wide_takes_two_cells(self):
        g = Grid(["a中b"])
        self.assertEqual([g.at(0, c) for c in range(4)], ["a", "中", "", "b"])

    def test_width(self):
        self.assertEqual(Grid(["a中b"]).width(0), 4)

    def test_out_of_range_is_none(self):
        g = Grid(["ab"])
        self.assertIsNone(g.at(0, 2))
        self.assertIsNone(g.at(0, -1))
        self.assertIsNone(g.at(1, 0))
        self.assertIsNone(g.at(-1, 0))

    def test_space_is_not_none(self):
        self.assertEqual(Grid(["a b"]).at(0, 1), " ")

    def test_empty_row(self):
        g = Grid([""])
        self.assertIsNone(g.at(0, 0))
        self.assertEqual(g.width(0), 0)

    def test_height_and_max_width(self):
        g = Grid(["ab", "中中中", ""])
        self.assertEqual(g.height, 3)
        self.assertEqual(g.max_width, 6)

    def test_empty_grid(self):
        g = Grid([])
        self.assertEqual(g.height, 0)
        self.assertEqual(g.max_width, 0)

    def test_combining_mark_shares_cell(self):
        g = Grid(["éx"])
        self.assertEqual(g.at(0, 0), "é")
        self.assertEqual(g.at(0, 1), "x")

    def test_zero_width_takes_no_cell(self):
        g = Grid(["a\x07b"])
        self.assertEqual(g.width(0), 2)
        self.assertEqual(g.at(0, 1), "b")

    def test_flag_two_cells(self):
        jp = "\U0001f1ef\U0001f1f5"
        g = Grid(["x" + jp + "y"])
        self.assertEqual(g.at(0, 1), jp)
        self.assertEqual(g.at(0, 2), "")
        self.assertEqual(g.at(0, 3), "y")

    def test_ambiguous_wide(self):
        self.assertEqual(Grid(["±x"]).width(0), 2)
        self.assertEqual(Grid(["±x"], ambiguous_wide=True).width(0), 3)

    def test_box_in_cjk_frame_aligns(self):
        g = Grid(["┌──┐", "│中│", "└──┘"])
        self.assertEqual(g.width(0), g.width(1))
        self.assertEqual(g.at(1, 3), "│")
        self.assertEqual(g.at(0, 3), "┐")


class Indexes(unittest.TestCase):
    def test_col_of_ascii(self):
        g = Grid(["abc"])
        self.assertEqual([g.col_of(0, i) for i in range(4)], [0, 1, 2, 3])

    def test_col_of_after_wide(self):
        g = Grid(["中ab"])
        self.assertEqual(g.col_of(0, 1), 2)
        self.assertEqual(g.col_of(0, 3), 4)

    def test_col_of_end_is_width(self):
        g = Grid(["a中"])
        self.assertEqual(g.col_of(0, 2), g.width(0))

    def test_col_of_inside_cluster(self):
        g = Grid(["éx"])
        self.assertEqual(g.col_of(0, 1), 0)
        self.assertEqual(g.col_of(0, 2), 1)

    def test_index_of_round_trip(self):
        g = Grid(["a中b"])
        for i in range(3):
            self.assertEqual(g.index_of(0, g.col_of(0, i)), i)

    def test_index_of_continuation_cell(self):
        g = Grid(["a中b"])
        self.assertEqual(g.index_of(0, 2), 1)

    def test_row_clusters(self):
        g = Grid(["a中"])
        self.assertEqual(g.row_clusters(0), [(0, "a", 1), (1, "中", 2)])


if __name__ == "__main__":
    unittest.main()
