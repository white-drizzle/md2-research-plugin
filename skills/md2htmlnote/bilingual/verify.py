#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""md2htmlnote bilingual-mode structural verifier.

Deterministic checks for a generated bilingual parallel-reading HTML file.
Complements (does not replace) the audit in references/bilingual.md.

Usage:
    python bilingual/verify.py bilingual.html [source.md]  # from the skill root

Exit code: 0 = all checks passed, 1 = one or more checks failed.

The optional source.md enables cross-checks (references / acknowledgement /
appendix presence). If omitted, only HTML-internal checks run.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reading_contract import check_reading_experience

# -- hard-coded invariants from template.html (edit template first, then here) --
LB_ONCLICK = ("document.getElementById('lb-img').src=this.src;"
              "document.getElementById('lightbox').classList.add('active')")
_BS = chr(92)
MATHJAX_CFG = "displayMath: [['$$','$$'], ['" + _BS + _BS + "[','" + _BS + _BS + "]']]"
STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
MATHBLOCK_TAG_RE = re.compile(r"\\tag\s*\{([^}]*)\}")
# 合法 6 色语义枚举（与 template.html 一致）
COLOR_NAMES = {"red", "blue", "green", "yellow", "purple"}
# 子图标记：半角 (a)，前置分隔符，后不跟字母数字（函数参数 y(t) 不误报）
SUB_MARK_RE = re.compile(
    r"(?:^|[;；。:：—]|&mdash;|<br\s*/?>)\s*\(([a-z])\)(?![A-Za-z0-9])",
    re.M)
FIG_NUM_RE = re.compile(r"图\s*(\d+)")


class Verifier:
    def __init__(self, html, md=None):
        self.html = html
        self.md = md
        self.errors = []
        self.warnings = []

    def check(self, cond, msg):
        if not cond:
            self.errors.append(msg)

    def note(self, msg):
        self.warnings.append(msg)

    def run(self):
        html = self.html
        m = STYLE_BLOCK_RE.search(html)
        style = m.group(1) if m else ""

        # ---- 1. div 平衡（词边界，注释/JS 里的 <div 子串不干扰）----
        n_open = len(re.findall(r"<div\b", html))
        n_close = html.count("</div>")
        self.check(n_open == n_close,
                   f"div imbalance: {n_open} opens vs {n_close} closes")

        # ---- 2. 无未解析 INSIGHT anchor ----
        self.check("<!-- INSIGHT:" not in html,
                   "unresolved <!-- INSIGHT: --> anchors remain")

        # ---- 3. 双语核心契约：original-text 数 == translated-text 数 ----
        n_orig = len(re.findall(r'class="[^"]*\boriginal-text\b', html))
        n_tran = len(re.findall(r'class="[^"]*\btranslated-text\b', html))
        self.check(n_orig == n_tran,
                   f"original-text count ({n_orig}) != translated-text count ({n_tran})；"
                   f"每个源段落必须 1:1 配对双语块")
        self.check(n_orig > 0, "no .original-text blocks found (page must be bilingual)")

        # ---- 4. 颜色合法性：bilingual-block.color-X 与 mark.hl-X 仅允许 5 色枚举 ----
        blocks = re.findall(r'class="([^"]*bilingual-block[^"]*)"', html)
        for cls in blocks:
            for name in re.findall(r"color-([a-z]+)", cls):
                self.check(name in COLOR_NAMES,
                           f"unknown bilingual-block color: color-{name}")
        marks = re.findall(r'class="(hl-[a-z]+)"', html)
        for mcls in marks:
            name = mcls[len("hl-"):]
            self.check(name in COLOR_NAMES,
                       f"unknown inline highlight class: {mcls}")

        # ---- 5. key-term 双语注释存在 ----
        self.check(re.search(r'class="[^"]*\bkey-term\b[^"]*"', html),
                   "no <span class=\"key-term\"> found — 关键术语首次出现必须双语标注")

        # ---- 6. ToC <-> heading 对应 ----
        tocs = re.findall(r'<a[^>]*href="#([^"]+)"', html)
        headings = re.findall(r'<h[23]\s+id="([^"]+)"', html)
        toc_set, head_set = set(tocs), set(headings)
        self.check(head_set <= toc_set,
                   f"headings missing from ToC: {sorted(head_set - toc_set)}")
        self.check(toc_set <= head_set,
                   f"ToC links with no target heading: {sorted(toc_set - head_set)}")

        # ---- 7. 每个 <img> 有 lightbox onclick + onerror ----
        imgs = re.findall(r"<img\b[^>]*>", html)
        srcs = []
        for tag in imgs:
            if 'id="lb-img"' in tag:
                continue
            if "onclick=" not in tag or "onerror=" not in tag:
                self.check(False, f"img missing onclick/onerror lightbox: {tag[:80]}")
            if LB_ONCLICK not in tag:
                self.check(False, f"img onclick differs from locked template: {tag[:80]}")
            srcm = re.search(r'\bsrc="([^"]+)"', tag)
            if srcm:
                srcs.append(srcm.group(1))
        real_srcs = [s for s in srcs if not s.startswith("data:image")]
        dups = {s for s in real_srcs if real_srcs.count(s) > 1}
        self.check(not dups, f"duplicate image URLs: {sorted(dups)}")

        # ---- 8. 公式：math-block == math-note；tag 唯一有序 ----
        blocks = re.findall(r'<div class="math-block">(.*?)</div>', html, re.S)
        notes = re.findall(r'<p class="math-note">.*?</p>', html, re.S)
        self.check(len(blocks) == len(notes),
                   f"math-block count ({len(blocks)}) != math-note count ({len(notes)})")
        tags = []
        for blk in blocks:
            tags.extend(MATHBLOCK_TAG_RE.findall(blk))
        if blocks:
            missing = len(blocks) - len(tags)
            if missing:
                # 论文中间推导（如 ε 动态块）可无编号；唯一/有序检查只作用于已编号公式
                self.note(f"display formulas without \\tag: {missing}（论文原样无编号的中间推导允许，"
                          f"唯一/有序检查仅作用于已编号公式）")
            self.check(len(set(tags)) == len(tags),
                       f"duplicate equation tags: {sorted(set(tags))}")
            nums = [t for t in tags if t.isdigit()]
            if len(nums) == len(tags):
                self.check(nums == sorted(nums, key=int),
                           f"equation numbers not ordered: {tags}")

        # ---- 9. MathJax 配置正确、无 async、无暗色模式 ----
        self.check("MathJax = {" in html, "MathJax config block missing")
        self.check(MATHJAX_CFG in html,
                   "MathJax displayMath must include BOTH ['$$','$$'] and ['\\\\[','\\\\]']")
        self.check("cdn.jsdelivr.net/npm/mathjax@3" in html,
                   "MathJax v3 script missing")
        mj_src = re.search(r'<script[^>]*src="[^"]*mathjax[^"]*"[^>]*>', html, re.I)
        if mj_src:
            self.check("async" not in mj_src.group(0),
                       "MathJax script must not be async")
        else:
            self.check(False, "MathJax v3 script tag not found")
        self.check("prefers-color-scheme: dark" not in html,
                   "dark mode CSS present (forbidden)")

        # ---- 10. insight-note 结构弱检查：每个含 ≥1 insight-section + 1 insight-personal ----
        self.check_insight_structure()

        # ---- 11. figure-row 面板数 <-> 统一 caption 子描述数 ----
        self.check_figure_rows()

        # ---- 12. 正文「图 N」<-> figcaption 双向交叉引用 ----
        self.check_figure_crossrefs()

        # ---- 13. source.md 交叉检查（可选）----
        if self.md:
            md = self.md
            if re.search(r"(?im)^#+\s*(references|bibliography)\b", md):
                self.check(re.search(r'id="refs"', html),
                           "source has a References section but #refs block is missing")
            if re.search(r"(?i)\backnowledg", md):
                self.check(re.search(r"(?i)\backnowledg", html),
                           "source has an Acknowledgement but the HTML does not")
            if re.search(r"(?i)appendix", md):
                self.check(re.search(r'id="app"', html) or re.search(r"(?i)appendix", html),
                           "source has an Appendix but no appendix section found")

        self.errors.extend(check_reading_experience(html))
        return not self.errors

    def check_insight_structure(self):
        """每个 .insight-note 必须含 ≥1 个 .insight-section 和 1 个 .insight-personal。

        3/5 分析维度（机制/定量/对比/实验设计/隐含假设）是 AI 判断，无法机械化——
        只做结构弱检查，维度要求由 SKILL.md 规则约束。
        用深度配对扫描定位每个 insight-note 的完整边界（内部嵌套 div 不截断）。
        """
        notes = []
        depth = 0
        start = None
        html = re.sub(r"<!--.*?-->", "", self.html, flags=re.S)  # 注释里的 <div 不干扰计数
        for m in re.finditer(r'<div\b[^>]*>|</div>', html):
            tag = m.group(0)
            if tag == '</div>':
                depth -= 1
                if depth == 0 and start is not None:
                    notes.append((start, m.start()))
                    start = None
            else:
                if depth == 0 and 'class="insight-note"' in tag:
                    start = m.start()
                depth += 1
        for i, (s, e) in enumerate(notes):
            body = html[s:e]
            n_section = body.count('<div class="insight-section">')
            has_personal = 'class="insight-personal"' in body
            self.check(n_section >= 1,
                       f"insight-note #{i+1} missing .insight-section (需要 ≥1 个分析维度小节)")
            self.check(has_personal,
                       f"insight-note #{i+1} missing .insight-personal (个人思考必填)")

    def check_figure_rows(self):
        """Panel count vs unified-caption sub-description count.

        逻辑与 md2htmlnote verify.py 相同：统一 caption 在 <figure> 外且带子图
        标记；面板数 = 该 caption 所属图组内 <figure> 数。全角标记/合并写法会
        计数不符而 FAIL。分析前剥离 <span class="fig-original"> 内的英文原文——
        原文中的 (a)(b) 是论文 caption 自带的，不算中文子描述。
        """
        html = re.sub(r"<!--.*?-->", "", self.html, flags=re.S)

        def strip_orig(cap):
            return re.sub(r"<span class=\"fig-original\">.*?</span>", "", cap, flags=re.S)

        rows = re.findall(r'<div class="figure-row">(.*?)</div>', html, re.S)
        if not rows:
            return
        figcaps = list(re.finditer(r"<figcaption[^>]*>(.*?)</figcaption>", html, re.S))
        unified = []
        bounds = [0]
        for m in figcaps:
            prefix = html[:m.start()]
            inside = prefix.count("<figure") > prefix.count("</figure>")
            f = strip_orig(m.group(1))
            if inside:
                if not SUB_MARK_RE.search(f):
                    bounds.append(m.end())
            else:
                # 图外 figcaption 的结束位置一律作为图组边界——单图 caption 无子图
                # 标记也必须入界，否则其后的 unified caption 会把前一个多面板图组的
                # <figure> 重复计入 panel_total（2026-08-11 完整跑发现的真实 bug）
                bounds.append(m.end())
                if SUB_MARK_RE.search(f):
                    unified.append(m)
        subcaps = []
        for m in unified:
            f = strip_orig(m.group(1))
            subcaps += SUB_MARK_RE.findall(f)
        panel_total = 0
        for m in unified:
            start = max(b for b in bounds if b <= m.start())
            seg = html[start:m.start()]
            panel_total += len(re.findall(r"<figure\b", seg))
        self.check(
            panel_total == len(subcaps),
            f"figure-row panel count ({panel_total}) != sub-description count ({len(subcaps)}); "
            f"检查 unified caption：子图标记是否合并写成了 (b)(d)、是否用了全角（a）、"
            f"分隔符（; ；。 ：）是否缺失；3 面板图需 1 个 figure-row + 1 个 standalone figure")

    def check_figure_crossrefs(self):
        """图号双向引用：figcaption 的图号 ↔ 正文「图 N」引用。"""
        html = re.sub(r"<!--.*?-->", "", self.html, flags=re.S)
        html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
        caps = re.findall(r"<figcaption[^>]*>(.*?)</figcaption>", html, re.S)
        figure_nums = set()
        for c in caps:
            figure_nums.update(FIG_NUM_RE.findall(c))
        if not figure_nums:
            return
        body = re.sub(r"<figcaption[^>]*>.*?</figcaption>", "", html, flags=re.S)
        cited = set(FIG_NUM_RE.findall(body))
        orphans = sorted(figure_nums - cited, key=int)
        dangling = sorted(cited - figure_nums, key=int)
        self.check(
            not orphans,
            f"orphan figures (有 figcaption 但正文未引用「图 N」): {orphans}；"
            f"每张图必须在正文有交叉引用，如「（图 N）」「如图 N 所示」")
        self.check(
            not dangling,
            f"dangling figure references (正文引用但无对应 figcaption): {dangling}；"
            f"正文「图 N」必须指向实际存在的图")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    html_path = sys.argv[1]
    md_path = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print(f"error: file not found: {html_path}")
        sys.exit(2)
    md = None
    if md_path:
        with open(md_path, encoding="utf-8") as f:
            md = f.read()
    v = Verifier(html, md)
    ok = v.run()
    if v.warnings:
        print("WARNINGS:")
        for w in v.warnings:
            print(f"  - {w}")
    if v.errors:
        print("FAIL:")
        for e in v.errors:
            print(f"  - {e}")
        sys.exit(1)
    print("PASS: all structural checks passed" + (f" ({len(v.warnings)} warning)" if v.warnings else ""))
    sys.exit(0)


if __name__ == "__main__":
    main()
