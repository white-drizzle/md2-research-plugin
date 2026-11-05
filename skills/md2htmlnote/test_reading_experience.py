"""Both modes must reject broken term help and detached visual references."""
import importlib.util
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent


def verifier(mode):
    path = ROOT / ('bilingual/verify.py' if mode == 'bilingual' else 'verify.py')
    spec = importlib.util.spec_from_file_location('verify_' + mode, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Verifier


def page(extra='', definitions='{"ps":{"title":"PS 印刷速度","description":"刮刀沿钢网移动的速度，单位 mm/s。"}}'):
    return r'''<script>MathJax = {tex: {displayMath: [['$$','$$'], ['\\[','\\]']]}};</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<nav class="toc-sidebar"><a href="#s1">引言</a><a href="#s2">方法</a></nav>
<main class="content"><h2 id="s1">引言</h2>
<div class="bilingual-block color-blue"><div class="original-text"><p>Print speed.</p></div>
<div class="lang-divider"></div><div class="translated-text"><p><span class="key-term">印刷速度</span>：
<span class="term" data-term="ps" tabindex="0">PS</span>。</p></div></div>
<div class="insight-note"><div class="insight-section"><h4>机制</h4><p>解释。</p></div>
<div class="insight-personal">个人思考。</div></div>
<p>图 1 展示速度与质量的关系。</p><figure><img src="one.png" loading="lazy"
onclick="document.getElementById('lb-img').src=this.src;document.getElementById('lightbox').classList.add('active')"
onerror="this.src='data:image/svg+xml,fallback'"><figcaption>图 1 — 速度</figcaption></figure>
<h2 id="s2">方法</h2>''' + extra + '''</main>
<script type="application/json" id="term-definitions">''' + definitions + '''</script>
<div id="term-tooltip" role="tooltip" hidden><strong class="term-tooltip-title"></strong><div class="term-tooltip-description"></div></div><script id="term-tooltip-runtime">/* fixture */</script>'''


class ReadingExperienceChecks(unittest.TestCase):
    def assert_contract(self, html, rejected):
        for mode in ('report', 'bilingual'):
            with self.subTest(mode=mode):
                v = verifier(mode)(html)
                ok = v.run()
                self.assertEqual(not ok, rejected, v.errors)

    def test_valid_local_page(self):
        self.assert_contract(page(), False)

    def test_undefined_term_is_rejected(self):
        self.assert_contract(page().replace('data-term="ps"', 'data-term="unknown"'), True)

    def test_keyboard_inaccessible_term_is_rejected(self):
        self.assert_contract(page().replace(' tabindex="0"', ''), True)

    def test_missing_runtime_is_rejected(self):
        self.assert_contract(page().replace('id="term-tooltip-runtime"', 'id="other"'), True)

    def test_missing_tooltip_content_nodes_is_rejected(self):
        self.assert_contract(page().replace('<strong class="term-tooltip-title"></strong>',''),True)

    def test_nonexecutable_runtime_is_rejected(self):
        self.assert_contract(page().replace('<script id="term-tooltip-runtime">','<script id="term-tooltip-runtime" type="application/json">'),True)

    def test_empty_runtime_is_rejected(self):
        self.assert_contract(page().replace('/* fixture */',''),True)

    def test_documented_first_use_combined_classes_pass(self):
        html=page().replace('<span class="key-term">印刷速度</span>','<span class="key-term term" data-term="ps" tabindex="0">印刷速度</span>')
        self.assert_contract(html,False)

    def test_glossary_text_is_not_body_figure_reference(self):
        self.assert_contract(page(definitions='{"ps":{"title":"PS","description":"原文图 9 中讨论的速度。"}}'),False)

    def test_empty_definition_is_rejected(self):
        self.assert_contract(page(definitions='{"ps":{"title":"PS","description":""}}'), True)

    def test_invalid_glossary_json_is_rejected(self):
        self.assert_contract(page(definitions='not json'), True)

    def test_repeated_term_uses_one_definition(self):
        self.assert_contract(page('<p><span class="term" data-term="ps" tabindex="0">PS</span></p>'), False)

    def test_ambiguous_abbreviation_can_have_distinct_keys(self):
        definitions='{"ps":{"title":"PS 速度","description":"印刷速度。"},"pressure":{"title":"PS 原文符号","description":"该处原文指印刷压力。"}}'
        self.assert_contract(page('<p><span class="term" data-term="pressure" tabindex="0">PS</span></p>',definitions), False)

    def test_figure_cited_only_in_another_section_is_rejected(self):
        html = page().replace('<h2 id="s2">方法</h2>', '')
        html = html.replace('<figure>', '<h2 id="s2">方法</h2><p>其他说明。</p><figure>')
        self.assert_contract(html, True)

    def test_table_without_local_explanation_is_rejected(self):
        self.assert_contract(page('<p>其他说明。</p><table><caption>表 1. 参数</caption><tr><td>45</td></tr></table>'), True)

    def test_numbered_external_table_title_is_rejected(self):
        self.assert_contract(page('<p>表 1. 参数</p><table><tr><td>45</td></tr></table>'),True)

    def test_table_and_figure_after_same_explanation_pass(self):
        extra = '<p>表 1 列出参数。</p><div style="overflow-x:auto"><table><caption>表 1. 参数</caption><tr><td>45</td></tr></table></div>'
        self.assert_contract(page(extra), False)

    def test_templates_include_the_interaction(self):
        for path in (ROOT / 'template.html', ROOT / 'bilingual/template.html'):
            with self.subTest(path=path):
                text = path.read_text(encoding='utf8')
                self.assertIn('id="term-tooltip"', text)
                self.assertIn('id="term-definitions"', text)
                self.assertIn('id="term-tooltip-runtime"', text)

    def test_both_modes_share_the_tooltip_runtime(self):
        scripts=[]
        for path in (ROOT/'template.html',ROOT/'bilingual/template.html'):
            match=re.search(r'<script id="term-tooltip-runtime">(.*?)</script>',path.read_text(encoding='utf8'),re.S)
            self.assertIsNotNone(match,'tooltip runtime missing')
            scripts.append(match[1])
        self.assertEqual(scripts[0],scripts[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
