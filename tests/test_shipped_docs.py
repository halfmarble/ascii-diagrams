"""The plugin's own documents give the checker nothing to report."""
import glob
import os
import sys
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "skills", "ascii-diagrams", "scripts"))

from asciidiagrams.blocks import mask_code_spans
from asciidiagrams.checks import check_text


class ShippedDocs(unittest.TestCase):
    def test_docs_have_no_findings(self):
        paths = [os.path.join(ROOT, "README.md"),
                 os.path.join(ROOT, "skills", "ascii-diagrams", "SKILL.md")]
        paths += sorted(glob.glob(os.path.join(ROOT, "skills", "ascii-diagrams", "references", "*.md")))
        self.assertGreaterEqual(len(paths), 3)
        for path in paths:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            findings = check_text(text, kind="markdown", path=path)
            self.assertEqual([], [(f.rule, f.line) for f in findings], path)


class MaskCodeSpans(unittest.TestCase):
    def test_masks_equal_length_pairs(self):
        self.assertEqual("a" + " " * 6 + "b", mask_code_spans("a `┌─` b"))
        self.assertEqual("x" + " " * 11 + "y", mask_code_spans("x ``a ` b`` y"))

    def test_unclosed_backtick_is_literal(self):
        self.assertEqual("a ` ┌", mask_code_spans("a ` ┌"))


if __name__ == "__main__":
    unittest.main()
