#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for md2htmlnote bilingual/verify.py.

Run from the skill root:  python -B bilingual/test_verify.py
Exit 0 = all green. Samples are minimal HTML fragments, not full templates.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify import Verifier  # noqa: E402


def check(html):
    """运行 Verifier 并返回 errors 列表（空 = 全部检查通过）。"""
    v = Verifier(html)
    v.run()
    return v.errors


# ── 最小合法双语页基线：所有必查元素齐备 ──

def minimal_page(extra="", img_src="https://cdn.example.com/fig1.jpg"):
    # 注意：HTML 里 JS 字符串写 ['\\[','\\]']（字面双反斜杠），verify.py 的
    # MATHJAX_CFG 按此匹配——f-string 中必须写 \\\\[ 才能生成 \\[。
    return f"""<!DOCTYPE html><html><head><script>
    MathJax = {{ tex: {{ displayMath: [['$$','$$'], ['\\\\[','\\\\]']] }} }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    </head><body>
    <nav class="toc-sidebar" id="toc-sidebar"><div class="toc-title">目录导航</div>
      <a href="#s1">1. 引言</a></nav>
    <main class="content">
      <script id="term-definitions" type="application/json">{{"quartz":{{"title":"石英","description":"本例中的石英材料。"}}}}</script>
      <div id="term-tooltip" role="tooltip" hidden><strong class="term-tooltip-title"></strong><div class="term-tooltip-description"></div></div>
      <script id="term-tooltip-runtime">/* fixture */</script>
      <h2 id="s1">1. 引言</h2>
      <p><span class="term" data-term="quartz" tabindex="0">Quartz</span></p>
      <div class="bilingual-block color-blue">
        <div class="original-text"><p>The furnace has <mark class="hl-blue">six tubes</mark>.</p></div>
        <div class="lang-divider"><span class="lang-tag">译文</span></div>
        <div class="translated-text"><p>炉膛配备<span class="key-term">六根石英管（Quartz Tubes）</span>。</p></div>
      </div>
      <div class="insight-note">
        <div class="insight-label"><span class="semantic-badge badge-green"></span> 深度解读</div>
        <div class="insight-section"><h4 class="insight-h4">物理机制</h4><p>解释。</p></div>
        <div class="insight-personal"><strong>💡 个人思考</strong><p>联想。</p></div>
      </div>
      <p>如图 1 所示。</p>
      <figure>
        <img src="{img_src}" alt="Fig 1" loading="lazy"
             onclick="document.getElementById('lb-img').src=this.src;document.getElementById('lightbox').classList.add('active')"
             onerror="this.src='data:image/svg+xml,fallback'">
        <figcaption>图 1 &mdash; 测试图</figcaption>
      </figure>
      <div class="math-block">\\[ E = mc^2 \\tag{{1}} \\]</div>
      <p class="math-note"><strong>解读：</strong>质能方程。</p>
      {extra}
    </main>
    </body></html>"""


class StructureChecks(unittest.TestCase):
    def test_div_balance_pass(self):
        self.assertEqual(check(minimal_page()), [])

    def test_div_imbalance_fails(self):
        html = minimal_page(extra="<div>")  # 多一个未闭合 div
        self.assertTrue(check(html), "div imbalance must FAIL")

    def test_unresolved_insight_anchor_fails(self):
        html = minimal_page(extra="<!-- INSIGHT: intro -->")
        self.assertTrue(check(html), "unresolved INSIGHT anchor must FAIL")


class BilingualPairingChecks(unittest.TestCase):
    def test_en_zh_pairing_pass(self):
        self.assertEqual(check(minimal_page()), [])

    def test_unpaired_translated_fails(self):
        html = minimal_page(extra=(
            '<div class="bilingual-block color-yellow">'
            '<div class="translated-text"><p>多余译文</p></div></div>'))
        self.assertTrue(check(html), "orphan translated-text must FAIL")

    def test_unpaired_original_fails(self):
        html = minimal_page(extra=(
            '<div class="bilingual-block color-yellow">'
            '<div class="original-text"><p>多余原文</p></div></div>'))
        self.assertTrue(check(html), "orphan original-text must FAIL")


class ColorValidityChecks(unittest.TestCase):
    def test_valid_colors_pass(self):
        self.assertEqual(check(minimal_page()), [])

    def test_unknown_block_color_fails(self):
        html = minimal_page(extra=(
            '<div class="bilingual-block color-pink">'
            '<div class="original-text"><p>x</p></div>'
            '<div class="lang-divider"></div>'
            '<div class="translated-text"><p>y</p></div></div>'))
        self.assertTrue(check(html), "unknown block color must FAIL")

    def test_unknown_mark_color_fails(self):
        html = minimal_page(extra='<mark class="hl-pink">x</mark>')
        self.assertTrue(check(html), "unknown mark color must FAIL")

    def test_no_keyterm_fails(self):
        html = minimal_page().replace('<span class="key-term">六根石英管（Quartz Tubes）</span>', '六根石英管')
        self.assertTrue(check(html), "missing key-term must FAIL")


class ToCChecks(unittest.TestCase):
    def test_toc_complete_pass(self):
        self.assertEqual(check(minimal_page()), [])

    def test_toc_dangling_link_fails(self):
        html = minimal_page(extra='<a href="#ghost">悬空链接</a>')
        self.assertTrue(check(html), "ToC link without heading must FAIL")

    def test_heading_missing_from_toc_fails(self):
        html = minimal_page(extra='<h2 id="s9">9. 附录</h2>')
        self.assertTrue(check(html), "heading missing from ToC must FAIL")


class FigureChecks(unittest.TestCase):
    def test_figure_with_citation_passes(self):
        html = minimal_page(extra='<p>如图 1 所示。</p>')
        self.assertEqual(check(html), [])

    def test_orphan_figure_fails(self):
        html = minimal_page().replace('<p>如图 1 所示。</p>', '')  # figcaption 图 1 但正文无「图 1」
        self.assertTrue(check(html), "orphan figure must FAIL")

    def test_duplicate_image_url_fails(self):
        html = minimal_page(extra=(
            '<p>如图 2 所示。</p>'
            '<figure><img src="https://cdn.example.com/fig1.jpg" alt="Fig 2" loading="lazy" '
            'onclick="document.getElementById(\'lb-img\').src=this.src;document.getElementById(\'lightbox\').classList.add(\'active\')" '
            'onerror="this.src=\'data:image/svg+xml,fallback\'"><figcaption>图 2 &mdash; 重复图</figcaption></figure>'))
        self.assertTrue(check(html), "duplicate image URL must FAIL")

    def test_img_missing_lightbox_fails(self):
        # img 缺 onclick/onerror → lightbox 契约失败
        html = minimal_page(extra=(
            '<p>如图 2 所示。</p>'
            '<figure><img src="https://cdn.example.com/fig2.jpg" alt="Fig 2">'
            '<figcaption>图 2 &mdash; 无 lightbox</figcaption></figure>'))
        self.assertTrue(check(html), "img without lightbox must FAIL")

    def test_dangling_reference_fails(self):
        # 正文引用不存在的图 9
        html = minimal_page(extra='<p>如图 9 所示。</p>')
        errs = check(html)
        self.assertTrue(any("9" in e for e in errs),
                        f"expected dangling 9 in errors: {errs}")


class FormulaChecks(unittest.TestCase):
    def test_formula_ok_pass(self):
        self.assertEqual(check(minimal_page()), [])

    def test_missing_math_note_fails(self):
        html = minimal_page(extra='<div class="math-block">\\[ x = 1 \\tag{2} \\]</div>')
        self.assertTrue(check(html), "math-block without math-note must FAIL")

    def test_formula_untagged_block_allowed(self):
        # 论文中间推导块可无 \tag（2026-08-11 完整跑：ε 动态块论文原样无编号）——
        # 降级为 warning，不 FAIL；编号唯一/有序仍强制
        html = minimal_page(extra=(
            '<div class="math-block">\\[ \\dot\\epsilon = -c_1 \\epsilon \\]</div>'
            '<p class="math-note"><strong>解读：</strong>观测误差动态。</p>'))
        v = Verifier(html)
        v.run()
        self.assertFalse(v.errors, "untagged intermediate formula must NOT FAIL")
        self.assertTrue(any("without \\tag" in w for w in v.warnings),
                        f"expected untagged warning: {v.warnings}")

    def test_formula_duplicate_tag_fails(self):
        # 编号重复仍必须 FAIL（唯一性不因无编号豁免而放松）
        html = minimal_page(extra=(
            '<div class="math-block">\\[ x = 1 \\tag{1} \\]</div>'
            '<p class="math-note"><strong>解读：</strong>x</p>'))
        self.assertTrue(check(html), "duplicate \\tag must FAIL")


class InsightChecks(unittest.TestCase):
    def test_insight_complete_pass(self):
        self.assertEqual(check(minimal_page()), [])

    def test_insight_missing_personal_fails(self):
        html = minimal_page().replace(
            '<div class="insight-personal"><strong>💡 个人思考</strong><p>联想。</p></div>', '')
        self.assertTrue(check(html), "insight without personal section must FAIL")

    def test_insight_missing_section_fails(self):
        html = minimal_page().replace(
            '<div class="insight-section"><h4 class="insight-h4">物理机制</h4><p>解释。</p></div>', '')
        self.assertTrue(check(html), "insight without insight-section must FAIL")


class DarkModeChecks(unittest.TestCase):
    def test_no_dark_mode_pass(self):
        self.assertEqual(check(minimal_page()), [])

    def test_dark_mode_fails(self):
        html = minimal_page(extra='<style>@media (prefers-color-scheme: dark) { body { background: #111; } }</style>')
        self.assertTrue(check(html), "dark mode must FAIL")

    def test_wrong_mathjax_displaymath_fails(self):
        # displayMath 缺 \\[ \\] 双定界符（覆盖默认数组）
        html = minimal_page().replace(
            "displayMath: [['$$','$$'], ['\\\\[','\\\\]']]",
            "displayMath: [['$$','$$']]")
        self.assertTrue(check(html), "displayMath missing \\\\[ \\\\] must FAIL")

    def test_mathjax_async_fails(self):
        html = minimal_page().replace(
            '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>',
            '<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>')
        self.assertTrue(check(html), "async MathJax script must FAIL")


class FigureRowChecks(unittest.TestCase):
    def test_figure_row_panels_pass(self):
        cap = '<figcaption>图 3 &mdash; (a) 温度；(b) 功率</figcaption>'
        html = minimal_page(extra=(
            '<p>如图 3 所示。</p>'
            '<div class="figure-row"><figure><img src="https://cdn.example.com/f3a.jpg" alt="Fig 3a" loading="lazy" '
            'onclick="document.getElementById(\'lb-img\').src=this.src;document.getElementById(\'lightbox\').classList.add(\'active\')" '
            'onerror="this.src=\'data:image/svg+xml,fallback\'"></figure>'
            '<figure><img src="https://cdn.example.com/f3b.jpg" alt="Fig 3b" loading="lazy" '
            'onclick="document.getElementById(\'lb-img\').src=this.src;document.getElementById(\'lightbox\').classList.add(\'active\')" '
            'onerror="this.src=\'data:image/svg+xml,fallback\'"></figure></div>'
            + cap))
        self.assertEqual(check(html), [])

    def test_figure_row_panel_mismatch_fails(self):
        # 2 面板但 unified caption 只有 1 个子描述 → 计数不符
        cap = '<figcaption>图 4 &mdash; (a) 温度</figcaption>'
        html = minimal_page(extra=(
            '<p>如图 4 所示。</p>'
            '<div class="figure-row"><figure><img src="https://cdn.example.com/f4a.jpg" alt="Fig 4a" loading="lazy" '
            'onclick="document.getElementById(\'lb-img\').src=this.src;document.getElementById(\'lightbox\').classList.add(\'active\')" '
            'onerror="this.src=\'data:image/svg+xml,fallback\'"></figure>'
            '<figure><img src="https://cdn.example.com/f4b.jpg" alt="Fig 4b" loading="lazy" '
            'onclick="document.getElementById(\'lb-img\').src=this.src;document.getElementById(\'lightbox\').classList.add(\'active\')" '
            'onerror="this.src=\'data:image/svg+xml,fallback\'"></figure></div>'
            + cap))
        self.assertTrue(check(html), "panel/sub-description mismatch must FAIL")

    def test_figure_row_panels_with_english_original_pass(self):
        # SKILL.md Step 5 格式：统一 caption 含 <span class="fig-original"> 英文原文，
        # 原文中的 (a)(b) 不得计入中文子描述计数
        cap = ('<figcaption>图 3 &mdash; (a) 温度分布；(b) 功率密度'
               '<br><span class="fig-original">(Original: Fig. 3: (a) Temperature distribution; (b) Power density)</span></figcaption>')
        html = minimal_page(extra=(
            '<p>如图 3 所示。</p>'
            '<div class="figure-row"><figure><img src="https://cdn.example.com/f3a.jpg" alt="Fig 3a" loading="lazy" '
            'onclick="document.getElementById(\'lb-img\').src=this.src;document.getElementById(\'lightbox\').classList.add(\'active\')" '
            'onerror="this.src=\'data:image/svg+xml,fallback\'"></figure>'
            '<figure><img src="https://cdn.example.com/f3b.jpg" alt="Fig 3b" loading="lazy" '
            'onclick="document.getElementById(\'lb-img\').src=this.src;document.getElementById(\'lightbox\').classList.add(\'active\')" '
            'onerror="this.src=\'data:image/svg+xml,fallback\'"></figure></div>'
            + cap))
        self.assertEqual(check(html), [])


    def test_figure_row_after_single_caption_pass(self):
        # 回归（2026-08-11 完整跑）：单图 caption 无子图标记（"图 2 &mdash; 单图题"），
        # 其后的 2 面板 figure-row 面板计数不得把前面图组的面板重复计入
        cap = '<figcaption>图 3 &mdash; (a) 温度；(b) 功率</figcaption>'
        html = minimal_page(extra=(
            '<p>如图 2 所示。</p>'
            '<figure><img src="https://cdn.example.com/f2.jpg" alt="Fig 2" loading="lazy" '
            'onclick="document.getElementById(\'lb-img\').src=this.src;document.getElementById(\'lightbox\').classList.add(\'active\')" '
            'onerror="this.src=\'data:image/svg+xml,fallback\'">'
            '<figcaption>图 2 &mdash; 单图无子图标记</figcaption></figure>'
            '<p>如图 3 所示。</p>'
            '<div class="figure-row"><figure><img src="https://cdn.example.com/f3a.jpg" alt="Fig 3a" loading="lazy" '
            'onclick="document.getElementById(\'lb-img\').src=this.src;document.getElementById(\'lightbox\').classList.add(\'active\')" '
            'onerror="this.src=\'data:image/svg+xml,fallback\'"></figure>'
            '<figure><img src="https://cdn.example.com/f3b.jpg" alt="Fig 3b" loading="lazy" '
            'onclick="document.getElementById(\'lb-img\').src=this.src;document.getElementById(\'lightbox\').classList.add(\'active\')" '
            'onerror="this.src=\'data:image/svg+xml,fallback\'"></figure></div>'
            + cap))
        self.assertEqual(check(html), [])


class SourceMdCrossChecks(unittest.TestCase):
    def test_refs_required_when_source_has_references(self):
        v = Verifier(minimal_page(), md="# Intro\n\n## References\n[1] x")
        v.run()
        self.assertTrue(v.errors, "source References but html lacks #refs → must FAIL")

    def test_refs_present_passes(self):
        html = minimal_page(extra='<a href="#refs">参考文献</a><h2 id="refs">参考文献</h2>')
        v = Verifier(html, md="# Intro\n\n## References\n[1] x")
        v.run()
        self.assertFalse(any("refs" in e for e in v.errors),
                         "html has #refs → no refs error expected")


if __name__ == "__main__":
    unittest.main(verbosity=2)
