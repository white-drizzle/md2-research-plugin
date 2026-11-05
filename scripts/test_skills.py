#!/usr/bin/env python3
"""Run the offline skill suites in separate processes using this interpreter.

Usage: python -B scripts/test_skills.py [--suite report|bilingual|pdf2md|md2pptnote]
Pillow and python-pptx must already be available. The PPT formula tests also
require local xelatex, pdfcrop and pdftoppm on PATH. Nothing is installed or uploaded.
"""

import argparse
import importlib
import inspect
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def run_pdf2md_tests():
    """Include unittest classes AND standalone functions, without pytest."""
    root = SKILLS / "pdf2md"
    sys.path.insert(0, str(root))
    suite = unittest.TestSuite()
    for file in sorted((root / "tests").glob("test_*.py")):
        module = importlib.import_module("tests." + file.stem)
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
        for name, function in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("test_") and not inspect.signature(function).parameters:
                suite.addTest(unittest.FunctionTestCase(function))

    # A few legacy functions use mkdtemp without cleanup. Contain their outputs.
    original_mkdtemp = tempfile.mkdtemp
    with tempfile.TemporaryDirectory(prefix="pdf2md-tests-") as scratch:
        def scoped_mkdtemp(suffix=None, prefix=None, dir=None):
            return original_mkdtemp(suffix=suffix or "", prefix=prefix or "case-", dir=dir or scratch)

        with patch("tempfile.mkdtemp", side_effect=scoped_mkdtemp):
            result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main():
    suites = {
        "report": (SKILLS / "md2htmlnote", ["-m", "unittest", "test_verify", "test_reading_experience", "test_multiview"]),
        "bilingual": (SKILLS / "md2htmlnote", ["bilingual/test_verify.py"]),
        "pdf2md": (SKILLS / "pdf2md", [str(Path(__file__).resolve()), "--pdf2md-worker"]),
        "md2pptnote": (SKILLS / "md2pptnote", ["tests/run_all.py"]),
    }
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=suites, action="append", help="Run only selected suites")
    parser.add_argument("--pdf2md-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.pdf2md_worker:
        return run_pdf2md_tests()

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    failed = []
    for name in args.suite or suites:
        cwd, arguments = suites[name]
        print(f"\n=== {name} ===", flush=True)
        result = subprocess.run([sys.executable, "-B", *arguments], cwd=cwd, env=env)
        if result.returncode:
            failed.append(name)
    print("\nFailed suites: " + ", ".join(failed) if failed else "\nAll skill suites passed.", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
