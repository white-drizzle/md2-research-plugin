"""Primary-model contact-sheet workflow: no external vision service is needed."""
import contextlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import fig_verify as fv


class NativeFigureWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / "_tmp" / "P1" / "raw"
        (self.raw / "images").mkdir(parents=True)
        for name, color in [("first.jpg", "red"), ("second.jpg", "blue")]:
            Image.new("RGB", (40, 30), color).save(self.raw / "images" / name)
        self.source = "# Paper\n\n![](images/first.jpg)\n\n![](images/second.jpg)\n\nFigure 1. a) first; b) second; c) merged.\n"
        (self.raw / "full.md").write_text(self.source, encoding="utf-8")
        self.report = "| Fig1 | 3 | 2 | 疑似 | 链接少 |\n"
        (self.raw / "fig_health.md").write_text(self.report, encoding="utf-8")

    def test_default_creates_contact_sheet_and_blank_mapping_without_rewriting(self):
        output = io.StringIO()
        original_mkdtemp = tempfile.mkdtemp
        def scoped_mkdtemp(*args, **kwargs):
            return original_mkdtemp(prefix="contact-", dir=self.root)
        with patch("tempfile.mkdtemp", side_effect=scoped_mkdtemp):
            with patch("subprocess.run", side_effect=AssertionError("default must not call an external process")):
                with contextlib.redirect_stdout(output):
                    rc = fv.main(str(self.raw))
        self.assertEqual(rc, 0)
        mapping_path = Path(re.search(r"映射模板: (.+)", output.getvalue()).group(1).strip())
        self.assertEqual(json.loads(mapping_path.read_text(encoding="utf-8")),
                         {"1": {"first.jpg": "", "second.jpg": ""}})
        with Image.open(mapping_path.parent / "fig1_contact.png") as sheet:
            self.assertGreater(sheet.width, 0)
        self.assertEqual((self.raw / "full.md").read_text(encoding="utf-8"), self.source)
        self.assertEqual((self.raw / "fig_health.md").read_text(encoding="utf-8"), self.report)
        self.assertFalse((self.raw / "full_fixed.md").exists())

    def test_missing_source_fails_before_creating_contact_outputs(self):
        (self.raw / "full.md").unlink()
        with patch("tempfile.mkdtemp", side_effect=AssertionError("missing source must fail before output")):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(fv.main(str(self.raw)), 1)
        self.assertEqual((self.raw / "fig_health.md").read_text(encoding="utf-8"), self.report)
        self.assertFalse((self.raw / "full_fixed.md").exists())

    def test_invalid_json_mapping_returns_failure_without_changing_source(self):
        mapping = self.root / "mapping.json"
        mapping.write_text("{invalid", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fv.apply_mapping_file(self.raw, "", str(mapping)), 1)
        self.assertEqual((self.raw / "full.md").read_text(encoding="utf-8"), self.source)
        self.assertEqual((self.raw / "fig_health.md").read_text(encoding="utf-8"), self.report)
        self.assertFalse((self.raw / "full_fixed.md").exists())

    def test_non_object_mapping_returns_failure_without_changing_source(self):
        mapping = self.root / "mapping.json"
        mapping.write_text('[{"first.jpg":"a"}]', encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fv.apply_mapping_file(self.raw, "", str(mapping)), 1)
        self.assertEqual((self.raw / "full.md").read_text(encoding="utf-8"), self.source)
        self.assertFalse((self.raw / "full_fixed.md").exists())


if __name__ == "__main__":
    unittest.main()

