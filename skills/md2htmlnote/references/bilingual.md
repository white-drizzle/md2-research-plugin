# Bilingual mode

Use for full parallel reading, translation comparison, and semantic color
annotation. Read [common.md](common.md) first. Template:
[../bilingual/template.html](../bilingual/template.html). Verifier/tests:
[../bilingual/verify.py](../bilingual/verify.py),
[../bilingual/test_verify.py](../bilingual/test_verify.py). Commands run from
the **skill root**; shared image helpers remain at that root.

## Full paragraph pairing

Preserve the complete original English and provide idiomatic academic Chinese
directly below it. Every source prose paragraph maps **1:1** to a
`.bilingual-block`; do not summarize, omit, or merge separate paragraphs.
Keep figures, formulas, tables, and source headings as separate ordered items.

```html
<div class="bilingual-block color-blue">
  <div class="original-text"><p>The sample was held at <mark class="hl-blue">300 K</mark>.</p></div>
  <div class="lang-divider"><span class="lang-tag">译文</span></div>
  <div class="translated-text"><p><span class="key-term">试样（sample）</span>保持在<mark class="hl-blue">300 K</mark>。</p></div>
</div>
```

Use Chinese for translations and interpretation; original English paragraphs,
original captions, headings, source metadata/references, and English term
annotations remain valid. Never apply the report-only Chinese prose rule to
`.original-text`. Preserve source meaning and technical precision while adapting
Chinese sentence structure. First-use `key-term` annotations belong in
translations and relevant figure captions.

Headings display **Chinese + space + original English**, preserving numbering.
Use stable IDs `sec-N` / `sec-N-M` for numbered sections and `sec-<english-slug>`
for unnumbered sections (for example `sec-abstract`). Keep all h2/h3 in the
ToC with `toc-h3` for subsections. Preserve the template's Chinese title,
original title, and metadata slots; include available keywords, dates, DOI,
and source citation without inventing missing details.

## Two-level semantic colors

For every paragraph choose its dominant role. Use one `color-X` class on the
`.bilingual-block`; neutral text deliberately has no color class. Preserve the
template's complete collapsible six-category legend.

| Class / inline class | Role | Typical content |
| --- | --- | --- |
| `color-red` / `hl-red` | Core | Research question, hypothesis, key conclusion, defining concept |
| `color-blue` / `hl-blue` | Method/data | Design, equipment, parameters, samples, metrics, numerical results |
| `color-green` / `hl-green` | Innovation | New contribution/framework and clearly identified personal connections |
| `color-yellow` / `hl-yellow` | Context | Background, prior work, secondary or provisional findings |
| `color-purple` / `hl-purple` | Critique | Limitations, caveats, future research, assumptions |
| No color class | Neutral | Transitional or already-known descriptive material |

Both levels matter: paragraph border/background plus `<mark class="hl-X">`
on significant sentences, numbers, or phrases. Highlight corresponding passages
in **both English and Chinese**, using matching semantic categories. Keep
similar roles consistent throughout the paper. For a mixed paragraph choose
the dominant, most specific role; if still tied use red > blue > green > yellow
> purple > neutral. Neutral is a judgment, not a shortcut for large sections.
Only the five named colors are valid; there is no `color-none`/`hl-none`.

## Deep insights and personal reflection

At each major section's end insert `.insight-note`, using `.insight-label`
and multiple `.insight-section` blocks with `.insight-h4` headings. Each note
must develop **at least three of five dimensions**, supported by the source:

1. Physical/engineering mechanism: explain why, using first principles.
2. Quantitative analysis: derive estimates/ratios from reported numbers and
   state assumptions.
3. Comparison: relate cited work or an identified benchmark to the contribution.
4. Experimental-design critique: strengths, missing controls, useful further
   characterization.
5. Hidden assumptions/limitations: validity boundaries and failure cases.

Every note also has `.insight-personal` with `个人思考`: research implications,
connections, or experiment ideas, clearly distinguished from author claims.
Notes must explain contributions, methods, results, and weaknesses rather
than repeat paragraph summaries. Do not fabricate comparison data.

## Figures, tables, and references

Follow the common six-step figure protocol. A figure's Chinese description
is followed by the **verbatim English source caption** in
`<span class="fig-original">(Original: ...)</span>` within its `<figcaption>`.
For multiple panels, place one unified bilingual caption after the last panel
row. English `(a)/(b)` markers inside `fig-original` do not count as additional
Chinese sub-descriptions in the bilingual verifier. Cite each figure in Chinese
body text as `图 N`, even when the paired English paragraph says `Figure N`.

Transcribe every source table and retain its original `Table N` number, data,
units, and math. Use `表 N &mdash; 中文标题` plus `fig-original` English title
above the table, with the template's horizontal-overflow wrapper when needed.
MinerU's raw `<table><tr><td>...` need not be converted to thead/tbody: the
bilingual CSS styles the first row. Keep `$...$` in cells for MathJax, and
cite `表 N` in body text (the verifier does not enforce table citations).
Clearly mark any additional analysis table as synthesis, not a numbered
source table. Preserve all reference entries and citation identifiers; use
the common rule preventing double numbering of `[N]` entries.

## Equations

Copy the bilingual template's synchronous MathJax setup with `tags: 'ams'`.
**Preserve original source `\tag{...}` exactly**, including nonsequential or
section-qualified numbering: source equation references depend on those tags.
Never renumber equations to the report sequence. Originally unnumbered
intermediate derivations are allowed; retain a `.math-note` after every block.
The bilingual verifier warns on unnumbered blocks, rejects duplicate tags,
and weakly checks order when all tags are integers. Report-only mandatory
numbering is not a bilingual requirement.

## Assembly, completeness, and controls

Use the common Python assembly strategy. First assemble paragraph pairs,
headings, figures, formulas, and tables; insert insights in a second pass at
explicit `<!-- INSIGHT: section-key -->` anchors. Resolve every anchor before
writing final output. For long section fragments, place the section insight
only in the final fragment and check item/heading counts after assembly.

Audit source/output parity for every paragraph, heading, image, formula, table,
and appendix; include **all** supporting information, acknowledgements/funding,
conflicts of interest, data availability, keywords, dates, and references.
Add an end-of-document numbered takeaway list with fewer than ten items.

Keep the template's language/note toolbar, expand/collapse-all, legend, mobile
ToC toggle, lightbox, back-to-top, and scripts intact. In native visual QA,
exercise all three independent toggles, both global actions, desktop ToC and
mobile ToC. Confirm every EN/ZH pair and matched inline highlight, legend
semantics, panel order, formula rendering, reference numbering, narrow-screen
readability, and the template's print presentation.

```text
python bilingual/verify.py "<bilingual.html>" "<registered-source.md>"
python -B bilingual/test_verify.py
```

Require exit 0, review warnings against the source, then finish native visual
QA. Do not run the report verifier against this output or rewrite source tags
to silence it. Structural checks are weaker than the full pairing, insight,
semantic-color, and source-completeness audit.
