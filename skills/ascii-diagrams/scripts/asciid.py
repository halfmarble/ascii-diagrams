#!/usr/bin/env python3
"""asciid: check and generate text diagrams.

  asciid.py check [paths|-] [--format text|json] [--max-width N] [--ambiguous-wide]
                  [--style] [--strict] [--plain]
  asciid.py gen <shape> [--style S] < payload.json
  asciid.py width [text|-]

Exit 0: no errors (and no warnings with --strict). 1: findings. 2: usage or I/O error.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import json
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from asciidiagrams import report
from asciidiagrams.checks import DEFAULT_RULES, check_text
from asciidiagrams.generators import SHAPES, STYLES, render
from asciidiagrams.width import clusters, display_width, split_lines, stability

EXTENSIONS = (".md", ".markdown", ".txt")
MARKDOWN_EXTENSIONS = (".md", ".markdown")


class UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def _build_parser() -> argparse.ArgumentParser:
    p = _Parser(prog="asciid", description="Check and generate text diagrams.")
    sub = p.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="check files, directories or stdin (-)")
    c.add_argument("paths", nargs="*")
    c.add_argument("--format", choices=("text", "json"), default="text")
    c.add_argument("--max-width", type=int, default=80)
    c.add_argument("--ambiguous-wide", action="store_true")
    c.add_argument("--style", action="store_true", help="also run the mixed-set and mixed-arrows rules")
    c.add_argument("--strict", action="store_true", help="warnings also give exit 1")
    c.add_argument("--plain", action="store_true", help="treat every file as one plain diagram block")
    g = sub.add_parser("gen", help="render a shape from a JSON payload on stdin")
    g.add_argument("shape", choices=SHAPES)
    g.add_argument("--style", choices=STYLES, default=None)
    w = sub.add_parser("width", help="per-line display width report")
    w.add_argument("text", nargs="?", default="-")
    return p


def _read_stdin() -> str:
    return sys.stdin.read()


def _read_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _collect(paths):
    """(display path, file path or None for stdin) pairs; a directory is walked."""
    out = []
    for p in paths:
        if p == "-":
            out.append(("<stdin>", None))
        elif os.path.isdir(p):
            found = []
            for root, dirs, files in os.walk(p):
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__"))
                for name in sorted(files):
                    if name.lower().endswith(EXTENSIONS):
                        found.append(os.path.join(root, name))
            out += [(f, f) for f in found]
        elif os.path.exists(p):
            out.append((p, p))
        else:
            raise OSError("no such file or directory: %s" % p)
    return out


def _kind(display: str, plain: bool) -> str:
    if plain:
        return "plain"
    if display == "<stdin>" or display.lower().endswith(MARKDOWN_EXTENSIONS):
        return "markdown"
    return "plain"


def cmd_check(a) -> int:
    paths = a.paths or ["-"]
    rules = set(DEFAULT_RULES)
    if a.style:
        rules |= {"mixed-set", "mixed-arrows"}
    results = []
    for display, real in _collect(paths):
        try:
            text = _read_stdin() if real is None else _read_file(real)
        except UnicodeDecodeError as e:
            raise OSError("%s: not UTF-8 text (%s)" % (display, e.reason))
        findings = check_text(text, display, _kind(display, a.plain), rules=rules,
                              max_width=a.max_width, ambiguous_wide=a.ambiguous_wide)
        results.append((display, findings))
    if a.format == "json":
        print(report.format_json(results))
    else:
        body = report.format_text(results)
        if body:
            print(body)
        print(report.summary(results))
    c = report.counts(results)
    if c["error"] or (a.strict and c["warning"]):
        return 1
    return 0


def cmd_gen(a) -> int:
    try:
        payload = json.loads(_read_stdin())
    except ValueError as e:
        raise UsageError("payload is not valid JSON: %s" % e)
    if a.style is not None and isinstance(payload, dict):
        payload["style"] = a.style
    try:
        out = render(a.shape, payload)
    except (ValueError, TypeError, KeyError, IndexError) as e:
        raise UsageError("cannot render %s: %s" % (a.shape, e))
    print(out)
    return 0


def cmd_width(a) -> int:
    text = _read_stdin() if a.text == "-" else a.text
    for i, line in enumerate(text.splitlines() or [""], 1):
        cells = display_width(line)
        marks = [c for c, _ in clusters(line) if stability(c) != "stable"]
        note = ""
        if marks:
            note = "  unstable/ambiguous: " + " ".join("U+%04X" % ord(c[0]) for c in marks)
        print("%3d  %3d chars  %3d cells  %s%s" % (i, len(line), cells, line, note))
    return 0


def main(argv=None) -> int:
    parser = _build_parser()
    try:
        a = parser.parse_args(argv)
        if a.cmd is None:
            raise UsageError("a command is required: check, gen or width")
        return {"check": cmd_check, "gen": cmd_gen, "width": cmd_width}[a.cmd](a)
    except UsageError as e:
        print("asciid: %s" % e, file=sys.stderr)
        return 2
    except OSError as e:
        print("asciid: %s" % e, file=sys.stderr)
        return 2
    except SystemExit as e:  # argparse --help
        return e.code if isinstance(e.code, int) else 0


if __name__ == "__main__":
    sys.exit(main())
