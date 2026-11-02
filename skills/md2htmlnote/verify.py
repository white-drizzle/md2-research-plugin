#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""md2htmlnote structural verifier.

Deterministic checks for a generated reading-note HTML file. Complements (does
not replace) the semantic content audit in SKILL.md: this catches mechanical
omissions the model might forget, so the audit no longer depends on it
"remembering".

Usage:
    python verify.py note.html [source.md]

Exit code: 0 = all checks passed, 1 = one or more checks failed.

The optional source.md enables cross-checks (keywords / references /
acknowledgement / appendix presence). If omitted, only HTML-internal checks run.
"""

import re
import sys

# -- hard-coded invariants from template.html (edit template first, then here) --
LB_ONCLICK = ("document.getElementById('lb-img').src=this.src;"
              "document.getElementById('lightbox').classList.add('active')")
# MathJax's displayMath config in template.html contains literal backslashes
# before '[' and ']'. In the HTML source the delimiters appear as ['\\[','\\]']
# (two backslash chars each, so the JS string '\[ ' reaches MathJax). Build the
# expected substring with chr(92) so no escaping layer can corrupt it.
_BS = chr(92)
MATHJAX_CFG = "displayMath: [['$$','$$'], ['" + _BS + _BS + "[','" + _BS + _BS + "]']]"
STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
MATHBLOCK_TAG_RE = re.compile(r"\\tag\s*\{([^}]*)\}")
# Sub-panel markers in unified captions: a single letter in half-width
# parentheses, PRECEDED by a separator (line start, ; ； 。 ： : — &mdash;
# <br>) and NOT followed by a letter/digit. Function arguments like y(t),
# u(t), y (t) are therefore never counted as markers. Bare whitespace is NOT
# a separator (y (t) would false-positive); \s* after a real separator
# supports "； (b)" spacing.
SUB_MARK_RE = re.compile(
    r"(?:^|[;；。:：—]|&mdash;|<br\s*/?>)\s*\(([a-z])\)(?![A-Za-z0-9])",
    re.M)
# In-text figure citations "图 N" (also matched inside figcaptions to number
# the figures). Whole-digit capture so 图 1 vs 图 10 never collide.
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

        # ---- 1. every <img> has lightbox onclick + onerror (verbatim strings) ----
        imgs = re.findall(r"<img\b[^>]*>", html)
        self.check(len(imgs) > 0, "no <img> tags found")
        srcs = []
        for tag in imgs:
            # the lightbox's own <img id="lb-img"> is intentionally empty
            if 'id="lb-img"' in tag:
                continue
            if "onclick=" not in tag or "onerror=" not in tag:
                self.check(False, f"img missing onclick/onerror lightbox: {tag[:80]}")
            if LB_ONCLICK not in tag:
                self.check(False, f"img onclick differs from locked template: {tag[:80]}")
            srcm = re.search(r'\bsrc="([^"]+)"', tag)
            if srcm:
                srcs.append(srcm.group(1))
        # data-URI fallbacks excluded from dedupe (they are inline SVGs)
        real_srcs = [s for s in srcs if not s.startswith("data:image")]
        dups = {s for s in real_srcs if real_srcs.count(s) > 1}
        self.check(not dups, f"duplicate CDN image URLs: {sorted(dups)}")

        # ---- 2. every .math-block has a following .math-note ----
        blocks = re.findall(r'<div class="math-block">(.*?)</div>', html, re.S)
        notes = re.findall(r'<p class="math-note">.*?</p>', html, re.S)
        self.check(len(blocks) == len(notes),
                   f"math-block count ({len(blocks)}) != math-note count ({len(notes)})")

        # ---- 3. every display formula has a unique, ordered \\tag{N} ----
        tags = []
        for blk in blocks:
            tags.extend(MATHBLOCK_TAG_RE.findall(blk))
        if blocks:
            self.check(len(tags) == len(blocks),
                       f"display formulas without \\tag: {len(blocks) - len(tags)} missing")
            self.check(len(set(tags)) == len(tags),
                       f"duplicate equation tags: {sorted(set(tags))}")
            nums = [t for t in tags if t.isdigit()]
            if len(nums) == len(tags):
                self.check(nums == sorted(nums, key=int),
                           f"equation numbers not ordered: {tags}")

        # ---- 4. MathJax config present, correct, and no async ----
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

        # ---- 5. no dark mode ----
        self.check("prefers-color-scheme: dark" not in html,
                   "dark mode CSS present (forbidden)")

        # ---- 6. ToC <-> heading correspondence ----
        tocs = re.findall(r'<a[^>]*href="#([^"]+)"', html)
        headings = re.findall(r'<h[23]\s+id="([^"]+)"', html)
        toc_set, head_set = set(tocs), set(headings)
        self.check(head_set <= toc_set,
                   f"headings missing from ToC: {sorted(head_set - toc_set)}")
        self.check(toc_set <= head_set,
                   f"ToC links with no target heading: {sorted(toc_set - head_set)}")

        # ---- 7. .figure-row panels <-> unified figcaption sub-descriptions ----
        self.check_figure_rows()

        # ---- 8. cross-checks with source.md (if provided) ----
        if self.md:
            md = self.md
            if re.search(r"(?im)^\s*keywords\s*:", md):
                self.check(re.search(r'class="keywords"', html),
                           "source has Keywords: but .keywords header line is missing")
            if re.search(r"(?im)^#+\s*(references|bibliography)\b", md):
                self.check(re.search(r'id="refs"', html),
                           "source has a References section but #refs block is missing")
            if re.search(r"(?i)\backnowledg", md):
                self.check(re.search(r"(?i)\backnowledg", html),
                           "source has an Acknowledgement but the HTML does not")
            if re.search(r"(?i)appendix", md):
                self.check(re.search(r'id="app"', html) or re.search(r"(?i)appendix", html),
                           "source has an Appendix but no appendix section found")

        # ---- 9. figure captions <-> in-text 图 N cross-references ----
        self.check_figure_crossrefs()

        return not self.errors

    def check_figure_rows(self):
        """Panel count vs unified-caption sub-description count.

        Panels = ALL <figure> tags in the figure group a unified caption
        belongs to (figure-row panels AND standalone <figure>s). A unified
        caption is a figcaption OUTSIDE any <figure> that carries sub-panel
        markers; plain single-figure captions (图 N &mdash;, inside their
        <figure>) are group boundaries. Per-figure captions inside a row
        ("(a) 子图描述" style) match SUB_MARK_RE but sit inside <figure>, so
        they are never unified and never boundaries.
        """
        html = re.sub(r"<!--.*?-->", "", self.html, flags=re.S)
        rows = re.findall(r'<div class="figure-row">(.*?)</div>', html, re.S)
        if not rows:
            return
        figcaps = list(re.finditer(r"<figcaption[^>]*>(.*?)</figcaption>", html, re.S))
        unified = []
        bounds = [0]
        for m in figcaps:
            prefix = html[:m.start()]
            inside = prefix.count("<figure") > prefix.count("</figure>")
            f = m.group(1)
            if inside:
                if not SUB_MARK_RE.search(f):
                    # plain single-figure caption -> previous group ends here
                    bounds.append(m.end())
            else:
                if SUB_MARK_RE.search(f):
                    unified.append(m)
                    bounds.append(m.end())
        subcaps = []
        for m in unified:
            subcaps += SUB_MARK_RE.findall(m.group(1))
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
        """Figure numbers in figcaptions <-> in-text 图 N citations.

        Every figure must be cited in the body (no orphan figures), and every
        in-text 图 N must point to an existing figcaption (no dangling
        references). Caption text is stripped before scanning the body, so a
        caption's own 图 N never counts as a citation. Pages with no figures
        are skipped.
        """
        html = re.sub(r"<!--.*?-->", "", self.html, flags=re.S)
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
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
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
