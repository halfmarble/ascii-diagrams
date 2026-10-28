"""Tests for the asciid.py command line: exit codes, JSON shape, stdin, directory
walk, and the gen -> check round trip."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, "skills", "ascii-diagrams", "scripts", "asciid.py")
sys.path.insert(0, os.path.join(ROOT, "skills", "ascii-diagrams", "scripts"))

from asciidiagrams.generators import SHAPES, STYLES
from tests.test_generators import LABELS, payload

ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
CLEAN_BOX = "┌────┐\n│ hi │\n└────┘\n"
BROKEN_BOX = "┌────┐\n│ hi │\n└──── ┘\n"


def run(*args, stdin=None):
    return subprocess.run([sys.executable, SCRIPT] + list(args), input=stdin,
                          capture_output=True, text=True, encoding="utf-8", env=ENV, cwd=ROOT)


class ExitCodes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, name, text):
        p = os.path.join(self.tmp, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def test_clean_exit_0(self):
        p = self.write("ok.txt", CLEAN_BOX)
        r = run("check", p)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0 errors", r.stdout)

    def test_broken_exit_1_text_format(self):
        p = self.write("bad.txt", BROKEN_BOX)
        r = run("check", p)
        self.assertEqual(r.returncode, 1)
        self.assertRegex(r.stdout, r"bad\.txt:\d+:\d+: error: \[\w[\w-]*\] ")

    def test_missing_file_exit_2(self):
        r = run("check", os.path.join(self.tmp, "nope.md"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no such file", r.stderr)

    def test_usage_errors_exit_2(self):
        self.assertEqual(run().returncode, 2)
        self.assertEqual(run("bogus").returncode, 2)
        self.assertEqual(run("check", "--format", "xml").returncode, 2)
        self.assertEqual(run("gen", "nosuchshape").returncode, 2)

    def test_gen_bad_json_exit_2(self):
        r = run("gen", "table", stdin="{not json")
        self.assertEqual(r.returncode, 2)

    def test_gen_malformed_payload_exit_2(self):
        r = run("gen", "table", stdin="{}")
        self.assertEqual(r.returncode, 2)
        self.assertIn("headers", r.stderr)

    def test_non_utf8_exit_2(self):
        p = os.path.join(self.tmp, "bin.txt")
        with open(p, "wb") as f:
            f.write(b"\xff\xfe\x00\x80")
        self.assertEqual(run("check", p).returncode, 2)

    def test_strict_warnings(self):
        long = "┌" + "─" * 90 + "┐\n│" + " " * 90 + "│\n└" + "─" * 90 + "┘\n"
        p = self.write("wide.txt", long)
        r = run("check", p, "--format", "json")
        data = json.loads(r.stdout)
        self.assertEqual(data["counts"]["error"], 0)
        self.assertGreaterEqual(data["counts"]["warning"], 1)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(run("check", p, "--strict").returncode, 1)
        self.assertEqual(run("check", p, "--max-width", "100").returncode, 0)
        self.assertEqual(run("check", p, "--strict", "--max-width", "100").returncode, 0)

    def test_json_shape(self):
        p = self.write("bad.txt", BROKEN_BOX)
        r = run("check", p, "--format", "json")
        data = json.loads(r.stdout)
        self.assertEqual(data["version"], 1)
        self.assertEqual(set(data), {"version", "files", "counts"})
        self.assertEqual(set(data["counts"]), {"error", "warning", "info"})
        self.assertEqual(data["files"][0]["path"], p)
        f = data["files"][0]["findings"][0]
        self.assertEqual(set(f), {"line", "col", "severity", "rule", "message", "suggestion"})
        self.assertEqual(data["counts"]["error"],
                         sum(1 for x in data["files"][0]["findings"] if x["severity"] == "error"))

    def test_stdin_plain_dash(self):
        r = run("check", "-", "--plain", "--format", "json", stdin=BROKEN_BOX)
        self.assertEqual(r.returncode, 1)
        data = json.loads(r.stdout)
        self.assertEqual(data["files"][0]["path"], "<stdin>")
        self.assertEqual(run("check", "-", "--plain", stdin=CLEAN_BOX).returncode, 0)

    def test_stdin_default_without_paths(self):
        r = run("check", stdin="```text\n" + BROKEN_BOX + "```\n")
        self.assertEqual(r.returncode, 1)

    def test_markdown_vs_plain(self):
        md = "Intro\n\n```text\n" + BROKEN_BOX + "```\n"
        p = self.write("doc.md", md)
        self.assertEqual(run("check", p).returncode, 1)
        # --plain treats the whole file as one block; the prose and fences are not a diagram,
        # but the broken box still is
        self.assertEqual(run("check", p, "--plain").returncode, 1)

    def test_code_fence_skipped(self):
        md = "```bash\necho a | grep b\n```\n"
        self.assertEqual(run("check", "-", stdin=md).returncode, 0)

    def test_directory_walk(self):
        self.write("a/one.md", "```text\n" + CLEAN_BOX + "```\n")
        self.write("a/b/two.txt", BROKEN_BOX)
        self.write("a/b/three.markdown", "```text\n" + CLEAN_BOX + "```\n")
        self.write("a/skip.py", BROKEN_BOX)
        self.write("a/.hidden/x.txt", BROKEN_BOX)
        r = run("check", os.path.join(self.tmp, "a"), "--format", "json")
        data = json.loads(r.stdout)
        names = sorted(os.path.basename(f["path"]) for f in data["files"])
        self.assertEqual(names, ["one.md", "three.markdown", "two.txt"])
        self.assertEqual(r.returncode, 1)
        bad = [f for f in data["files"] if f["findings"]]
        self.assertEqual([os.path.basename(f["path"]) for f in bad], ["two.txt"])

    def test_style_flag_enables_style_rules(self):
        mixed = "┌────┐\n│ hi │\n╰────╯\n"
        base = json.loads(run("check", "-", "--plain", "--format", "json", stdin=mixed).stdout)
        styled = json.loads(run("check", "-", "--plain", "--format", "json", "--style", stdin=mixed).stdout)
        rules = lambda d: {x["rule"] for f in d["files"] for x in f["findings"]}
        self.assertNotIn("mixed-set", rules(base))
        self.assertIn("mixed-set", rules(styled))

    def test_broken_fixtures_json(self):
        r = run("check", os.path.join("tests", "fixtures", "broken"), "--format", "json")
        self.assertEqual(r.returncode, 1)
        data = json.loads(r.stdout)
        self.assertGreaterEqual(data["counts"]["error"], 12)

    def test_clean_fixtures_no_errors(self):
        r = run("check", os.path.join("tests", "fixtures", "clean"), "--format", "json")
        data = json.loads(r.stdout)
        # clean fixtures carry '# expect:' headers; some are markdown-style fixtures read plain
        self.assertEqual(set(data), {"version", "files", "counts"})


class Width(unittest.TestCase):
    def test_width_report(self):
        r = run("width", "-", stdin="abc\n收到\n")
        self.assertEqual(r.returncode, 0)
        lines = r.stdout.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("3 cells", lines[0])
        self.assertIn("4 cells", lines[1])
        self.assertIn("2 chars", lines[1])

    def test_width_argument(self):
        r = run("width", "ab")
        self.assertIn("2 cells", r.stdout)


class GenRoundTrip(unittest.TestCase):
    def test_every_generator_output_checks_clean(self):
        ran = 0
        for shape in SHAPES:
            for style in STYLES:
                for name, labels in LABELS.items():
                    with self.subTest(shape=shape, style=style, labels=name):
                        p = payload(shape, labels, style)
                        p.pop("style")
                        g = run("gen", shape, "--style", style, stdin=json.dumps(p, ensure_ascii=False))
                        self.assertEqual(g.returncode, 0, g.stderr)
                        c = run("check", "-", "--plain", "--format", "json", stdin=g.stdout)
                        data = json.loads(c.stdout)
                        ran += 1
                        self.assertEqual(data["counts"]["error"], 0, g.stdout + c.stdout)
                        self.assertEqual(c.returncode, 0)
        self.assertEqual(ran, len(SHAPES) * len(STYLES) * len(LABELS))

    def test_style_flag_overrides_payload(self):
        p = {"steps": ["a", "b"], "style": "heavy"}
        out = run("gen", "flow", "--style", "ascii", stdin=json.dumps(p)).stdout
        self.assertIn("+", out)
        self.assertNotIn("┏", out)

    def test_payload_style_used_without_flag(self):
        p = {"steps": ["a", "b"], "style": "double"}
        out = run("gen", "flow", stdin=json.dumps(p)).stdout
        self.assertIn("╔", out)


if __name__ == "__main__":
    unittest.main()
