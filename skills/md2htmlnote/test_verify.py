#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for verify.py figure-row / unified-caption checks.

Run:  python test_verify.py
Exit 0 = all green. Focuses on check_figure_rows() (the sub-panel marker
counting logic); samples are minimal HTML fragments, not full templates.

The P1 regression resolves the current HTML artifact and its matching raw
linked.md from the project's _tmp/MANIFEST.json/current.json contract.
"""

import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify import SUB_MARK_RE, Verifier  # noqa: E402

# -- minimal samples: figure rows + unified captions only (no full template) --

ROW = ('<div class="figure-row"><figure><img src="u1.jpg"></figure>'
       '<figure><img src="u2.jpg"></figure></div>')


def _project_root():
    """Find the project containing the pipeline manifest from the test cwd."""
    for candidate in (Path.cwd(), *Path.cwd().parents):
        if (candidate / "_tmp" / "MANIFEST.json").is_file():
            return candidate
    raise unittest.SkipTest("project _tmp/MANIFEST.json not found")


def _p1_paths():
    """Resolve P1's current HTML and its registered raw linked.md."""
    root = _project_root()
    with (root / "_tmp" / "MANIFEST.json").open(encoding="utf-8") as f:
        manifest = json.load(f)
    paper = next(p for p in manifest["papers"] if p.get("id") == "P1")

    linked_md = root / paper["linked_md"]
    html = paper["html"]
    current_path = root / html["current"]
    with current_path.open(encoding="utf-8") as f:
        current = json.load(f)
    version_id = current.get("current_version")
    version = next(v for v in html["versions"] if v.get("id") == version_id)
    html_path = root / version["output"]
    return html_path, linked_md


def fig4panels(caption):
    return ROW + ROW + caption


def fig3panels(caption):  # 1 row (a,b) + 1 standalone (c)
    return ROW + '<figure><img src="u3.jpg"></figure>' + caption


def fig5panels(caption):  # 2 rows (a,b)+(c,d) + 1 standalone (e)
    return ROW + ROW + '<figure><img src="u5.jpg"></figure>' + caption


UNIFIED = ('<figcaption style="text-align:center;">图 N &mdash; 标题：'
           '{subs}</figcaption>')


class FigureRowChecks(unittest.TestCase):
    def check(self, html):
        v = Verifier(html)
        v.check_figure_rows()
        return v.errors

    def test_four_panels_halfwidth_markers_pass(self):
        cap = UNIFIED.format(subs="(a) 实测温度 y(t)；(b) 输入时滞 τ 的存在；(c) 控制输入 u(t)；(d) 时滞细节（约 1.603 s）")
        self.assertEqual(self.check(fig4panels(cap)), [])

    def test_three_panels_row_plus_standalone_pass(self):
        cap = UNIFIED.format(subs="(a) 观测输出 ŷ(t) 与实测输出 y(t); (b) 观测误差 ε(t); (c) 估计的扰动 w(t)")
        self.assertEqual(self.check(fig3panels(cap)), [])

    def test_five_panels_two_rows_plus_standalone_pass(self):
        cap = UNIFIED.format(subs="(a) x; (b) x; (c) x; (d) x; (e) x")
        self.assertEqual(self.check(fig5panels(cap)), [])

    def test_function_args_not_counted_as_markers(self):
        # y(t) / u(t) must NOT be treated as sub-panel markers
        cap = UNIFIED.format(subs="(a) 输出 y(t)；(b) 输入 u(t)")
        self.assertEqual(self.check(ROW + cap), [])

    def test_function_args_with_space_not_counted(self):
        cap = UNIFIED.format(subs="(a) 输出 y (t) 对比; (b) 输入 u (t)")
        self.assertEqual(self.check(ROW + cap), [])

    def test_merged_bd_markers_fail(self):
        cap = UNIFIED.format(subs="(a) x；(b)(d) 输入时滞 τ 的存在；(c) x")
        errs = self.check(fig4panels(cap))
        self.assertTrue(errs, "merged (b)(d) must FAIL")
        self.assertIn("(b)(d)", errs[0])

    def test_fullwidth_marker_fails(self):
        cap = UNIFIED.format(subs="(a) x; (b) x；）（c）估计的扰动 w")
        errs = self.check(fig3panels(cap))
        self.assertTrue(errs, "fullwidth （c） must FAIL")
        self.assertIn("全角", errs[0])

    def test_single_figure_without_figurerow_skipped(self):
        html = '<figure><img src="u1.jpg"></figure><figcaption>图 1 &mdash; 单图</figcaption>'
        self.assertEqual(self.check(html), [])


class FigureCrossrefChecks(unittest.TestCase):
    def check(self, html):
        v = Verifier(html)
        v.check_figure_crossrefs()
        return v.errors

    def test_figure_with_citation_passes(self):
        html = ('<p>结果如图 1 所示。</p>'
                '<figure><img src="u1.jpg"></figure>'
                '<figcaption>图 1 &mdash; 测试图</figcaption>')
        self.assertEqual(self.check(html), [])

    def test_orphan_figure_fails(self):
        html = ('<p>没有引用。</p>'
                '<figure><img src="u1.jpg"></figure>'
                '<figcaption>图 1 &mdash; 测试图</figcaption>')
        errs = self.check(html)
        self.assertTrue(errs, "orphan figure must FAIL")
        self.assertIn("1", errs[0])

    def test_dangling_reference_fails(self):
        html = ('<p>如图 9 所示。</p>'
                '<figure><img src="u1.jpg"></figure>'
                '<figcaption>图 1 &mdash; 测试图</figcaption>')
        errs = self.check(html)
        self.assertTrue(errs, "dangling reference must FAIL")
        self.assertTrue(any("9" in e for e in errs),
                        f"expected dangling 9 in errors: {errs}")

    def test_caption_not_counted_as_citation(self):
        # "图 2" appears only inside a figcaption -> figures stay orphaned
        html = ('<p>正文无引用。</p>'
                '<figure><img src="u1.jpg"></figure>'
                '<figcaption>图 1 &mdash; 如图 2 所示的效果</figcaption>')
        errs = self.check(html)
        self.assertTrue(errs, "caption text must not count as body citation")
        self.assertIn("1", errs[0])

    def test_no_figures_skipped(self):
        self.assertEqual(self.check("<p>无图页面。</p>"), [])


class P1Regression(unittest.TestCase):
    def test_p1_full_note_passes(self):
        manifest_html, linked_md = _p1_paths()
        path = Path(os.environ["P1_HTML"]) if "P1_HTML" in os.environ else manifest_html
        if not path.is_file() or not linked_md.is_file():
            self.skipTest(f"P1 artifacts not found: html={path}, linked_md={linked_md}")
        with path.open(encoding="utf-8") as f:
            html = f.read()
        with linked_md.open(encoding="utf-8") as f:
            md = f.read()
        v = Verifier(html, md)
        self.assertTrue(v.run(), "P1 成品必须通过全部结构检查")


if __name__ == "__main__":
    unittest.main(verbosity=2)
