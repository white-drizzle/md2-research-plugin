---
name: md2htmlnote
description: 'Use when a MinerU-exported Markdown paper with images and LaTeX needs an HTML study report or a full bilingual parallel-reading page with semantic colors. Triggers: HTML阅读笔记, 核心解读, 学习汇报, 双语阅读, 对照翻译, 语义标注, 颜色编码, bilingual reading, parallel translation, comparative reading.'
---

# Markdown to HTML Reading Page

Produce one HTMLnote that opens with **文献鸟瞰** and switches between the
paper graph, paper-specific flow, layered reading and **精读解析**. Select
one of two content modes for the complete analytical reader:

| Request | Mode | Read next | Locked template | Verifier |
| --- | --- | --- | --- | --- |
| Ordinary HTML note, core interpretation, advisor/study report; no explicit bilingual request | **report (default)** | [Report rules](references/report.md) | `template.html` | `verify.py` |
| Explicit bilingual / parallel reading / 对照翻译 / 双语, or semantic color annotation | **bilingual** | [Bilingual rules](references/bilingual.md) | `bilingual/template.html` | `bilingual/verify.py` |

An explicit bilingual request selects bilingual resources even when it also
mentions notes, interpretation, or a report. If both outputs are requested,
produce and verify each separately. Bilingual term annotations alone retain
report mode. Modes are authoring choices, not script flags.

Read [Common rules](references/common.md), [reading experience](references/reading-experience.md), and the selected mode's reference,
then read its actual template before assembly. All command paths are relative
to this skill root. Use the root `link_images.py` and `embed_base64.py` in either
mode; do not look for copies under `bilingual/`.

1. Resolve the paper's source and HTML version through `_tmp/MANIFEST.json`:
   registered `linked_fixed_md` first, otherwise `linked_md`. Write to the
   registered `P<n>/html/versions/<html-version>/` output and respect the
   registered `html/current.json` pointer. Details are in the common rules.
2. Copy the selected template's CSS, wrappers, controls, and JavaScript exactly;
   fill only content slots. Preserve all substantive source content and audit
   figures, tables, formulas, references, and back matter.
   Build a source-grounded term dictionary and mark recurring technical terms,
   abbreviations and parameter headers for hover/focus/tap explanations. Place
   each figure/table after its explanatory paragraph in the corresponding
   body section; keep original numbers, units and data. See the shared reading
   contract for the exact markup and placement recipe.
3. Apply only the selected mode's content contract. **Report:** Chinese
   interpretation with `.insight` boxes and sequential explicit `\tag{1}`,
   `\tag{2}`, … on every display formula. **Bilingual:** full original/Chinese
   paragraph pairs, two-level semantic colors, `.insight-note` analysis, and
   working toggles; preserve source equation tags and allow originally
   unnumbered derivations. English original text and captions are required in
   bilingual mode.
4. Save the complete reader to an authoring file. Follow
   [Four-view HTMLnote](references/multiview.md) to write the paper-specific
   guide JSON. Run `build_multiview.py reader.html guides.json -o <registered-output>`
   (add `--pdf <source.pdf>` when available). Deliver the resulting single
   file by default. When explicitly asked for the standalone reader, deliver
   the selected content-mode output directly.
5. Run **only the selected content mode's verifier** on the registered output
   with its resolved source Markdown. Check the guide claims, evidence,
   reader anchors and PDF pages against the same paper.
6. Perform native visual QA: open the real artifact, check loaded DOM, images
   and MathJax, inspect desktop/mobile screenshots and controls, crop uncertain
   regions, fix the generation source and re-render. The concise procedure and
   failure reporting are in [Common rules](references/common.md#native-visual-qa).

Follow a guide link to its specific section, figure or table, then return and
check the selected node, stage or expanded topics. Return the mode, versioned artifact path, source path, verifier result, visual
checks performed, and any unresolved or unverified items. Do not claim visual
or formula-rendering success from a structural pass alone.
