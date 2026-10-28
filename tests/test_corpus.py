"""Every fixture under tests/fixtures: broken ones give exactly the findings
their `# expect:` line names, clean ones give none.

Header lines (part of the checked text):
  # expect: rule@line:col, rule@line:col     (empty for a clean fixture)
  # kind: markdown                           (default: plain)
  # opts: max_width=N ambiguous_wide=1 rules=all
"""
import glob
import os
import sys
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "ascii-diagrams", "scripts"))

from asciidiagrams.checks import ALL_RULES, DEFAULT_RULES, check_text

FIXTURES = os.path.join(HERE, "fixtures")


def load(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    expect, kind, kw = [], "plain", {}
    for line in text.split("\n"):
        if line.startswith("# expect:"):
            expect = [x.strip() for x in line[len("# expect:"):].split(",") if x.strip()]
        elif line.startswith("# kind:"):
            kind = line[len("# kind:"):].strip()
        elif line.startswith("# opts:"):
            for pair in line[len("# opts:"):].split():
                key, value = pair.split("=")
                if key == "max_width":
                    kw["max_width"] = int(value)
                elif key == "ambiguous_wide":
                    kw["ambiguous_wide"] = value == "1"
                elif key == "rules":
                    kw["rules"] = ALL_RULES if value == "all" else DEFAULT_RULES
    return text, expect, kind, kw


def fixtures(kind):
    return sorted(glob.glob(os.path.join(FIXTURES, kind, "*.txt")))


class Corpus(unittest.TestCase):
    def test_enough_fixtures(self):
        self.assertGreaterEqual(len(fixtures("broken")), 12)
        self.assertGreaterEqual(len(fixtures("clean")), 8)

    def test_every_regression_has_a_fixture(self):
        names = {os.path.basename(p)[:-4] for p in fixtures("broken") + fixtures("clean")}
        wanted = {
            "cjk_padded_by_chars", "border_shifted_two_rows",
            "open_boxes_balanced_corners", "dangling_corner",
            "arrowhead_beside_box", "file_tree", "markdown_fences",
            "double_frame_light_boxes", "emoji_in_frame", "zwj_family_and_flag",
            "ascii_box_shifted_right", "ascii_two_boxes_shifted", "ascii_two_boxes",
            "tree_heavy_double", "bare_md_diagram", "indented_md_box",
        }
        self.assertEqual(wanted - names, set())

    def test_broken_fixtures_give_exactly_their_findings(self):
        for path in fixtures("broken"):
            text, expect, kind, kw = load(path)
            got = ["%s@%d:%d" % (f.rule, f.line, f.col) for f in check_text(text, path, kind, **kw)]
            name = os.path.basename(path)
            self.assertTrue(expect, name + " names no expected finding")
            self.assertEqual(sorted(got), sorted(expect), name)

    def test_clean_fixtures_give_none(self):
        for path in fixtures("clean"):
            text, expect, kind, kw = load(path)
            self.assertEqual(expect, [], os.path.basename(path))
            got = ["%s@%d:%d" % (f.rule, f.line, f.col) for f in check_text(text, path, kind, **kw)]
            self.assertEqual(got, [], os.path.basename(path))

    def test_broken_fixtures_have_errors_overall(self):
        errors = 0
        for path in fixtures("broken"):
            text, _, kind, kw = load(path)
            errors += sum(1 for f in check_text(text, path, kind, **kw) if f.severity == "error")
        self.assertGreaterEqual(errors, 12)

    def test_wide_char_and_flag_fixtures_are_warnings_only(self):
        for name in ("emoji_in_frame", "zwj_family_and_flag"):
            path = os.path.join(FIXTURES, "broken", name + ".txt")
            text, _, kind, kw = load(path)
            sev = {f.severity for f in check_text(text, path, kind, **kw)}
            self.assertEqual(sev, {"warning"}, name)


if __name__ == "__main__":
    unittest.main()
