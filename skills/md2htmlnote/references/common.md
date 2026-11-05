# Shared HTML rules

Read this with the selected [report](report.md) or [bilingual](bilingual.md)
reference. Commands below run from the **md2htmlnote skill root**, including
when authoring bilingual output.

## Source and output paths

- Resolve the paper and artifact version from the project's `_tmp/MANIFEST.json`.
  Consume `linked_fixed_md` **when registered**, otherwise `linked_md`. Never
  choose a fixed file merely because it exists. The shared raw boundary is
  `_tmp/P<n>/raw/` (`full.md`, `linked.md`, `images/`, `fig_health.md`, and
  registered fixed copies); preserve original inputs.
- Both modes write the registered HTML artifact under
  `_tmp/P<n>/html/versions/<html-version>/P<n>_<short-name>_<year>.html`.
  Resolve actual paths from MANIFEST rather than assuming the HTML is directly
  under `P<n>/`. Use the project's existing registration procedure; do not
  invent fields or a second manifest schema.
  For a new project, copy the minimal
  [registered example](../../../examples/registered-paper/README.md) first.
- `_tmp/P<n>/html/current.json` is the current pointer. `current_version` is a
  registered ID in this paper's `html.versions[]`, or JSON `null`; it cannot be
  omitted, empty, or a deck version ID. HTML and deck version IDs are independent.
  A deck reads the MANIFEST-registered current HTML header.
- Follow the project's pipeline-layout specification when present. Run existing
  `_tmp/scripts/pipeline_layout.py <project-root>` and
  `_tmp/scripts/check_image_refs.py <project-root>` gates when supplied; do not
  manufacture replacement scripts or registration formats.

## Locked templates and assembly

Use [../template.html](../template.html) for report and
[../bilingual/template.html](../bilingual/template.html) for bilingual. Copy the
selected `<style>` block byte-for-byte and retain its skeleton, class names,
element order, attributes, controls, MathJax configuration, and JavaScript.
Fill its content slots and populate source-dependent headings/metadata; omit
metadata absent from the source. Do not redesign the layout, add dark mode,
or change template CSS/JS to accommodate content.

Generate UTF-8 with a Python assembly script and structured content. Keep
LaTeX backslashes intact. Insert content via explicit template/section anchors;
fix the assembly source and regenerate instead of running broad regex edits
over finished HTML. Remove unused instructional example comments from generated
output: verifier scans can otherwise count their sample images or formulas.
Do not leave unresolved `FILL`, `CONTENT`, `TOC_LINKS`, or `INSIGHT` anchors.

For long papers, assemble section fragments at complete block boundaries
(roughly 20 paragraphs per fragment, fewer for formula-heavy sections).
Fragments contain body content only, their own h2/h3 headings, and section
insights at the section end. Compare an ordered source inventory of paragraphs,
headings, formulas, figures, and tables with the assembled output. Repair a
small omission through an idempotent anchor insertion in the generator rather
than rewriting unrelated fragments.

## Navigation, identity, and technical prose

Apply [reading-experience.md](reading-experience.md) in both modes: source-grounded
term explanations on hover/focus/tap, visible first-use definitions and units,
and figures/tables interleaved with their explanatory body paragraphs. Copy
the tooltip runtime from the selected template and fill its JSON dictionary.

- Give every h2/h3 a unique ID and matching sidebar link; indent h3 links with
  `toc-h3`. Heading IDs and ToC targets must match in both directions.
- Preserve the Chinese title, original title, available citation metadata,
  dates, and keywords. Never invent authors, affiliations, DOI, journal metrics,
  or publication details. A known DOI is a clickable `https://doi.org/<DOI>`
  link with `target="_blank"`; omit unavailable fields. Mode-specific headers
  are defined in the selected reference.
- Annotate a technical term's first occurrence in Chinese prose as
  `<span class="key-term term" data-term="term-key" tabindex="0">中文术语（English Term）</span>`;
  repeated terms can use `.term` without repeating the English expansion.
  Explanations should address mechanisms, quantitative meaning,
  and research relevance in professional academic Chinese. Retain source
  English in bilingual originals/captions and in titles, citations, references,
  symbols, and term annotations where needed.
- End with the template's source citation footer, using real source details.

## Images and multi-panel figures

Place the complete figure group directly after the body paragraph that explains
it, in the relevant method/result section. The paragraph cites `图 N` and names
what the reader should inspect. Do not use the template's instructional figure
examples as a separate end-of-page gallery. Keep source-caption and panel rules
below when moving the figure into its narrative context.

MinerU emits image lines and captions separately. Pair an image pool with its
nearest following `Figure`/`FIGURE` caption; exclude publisher logos and other
header metadata images before the abstract. Keep an inventory of every unique
content image so embedding does not conceal duplicate or missing panels.

1. **Collect:** between consecutive figure captions gather all image references
   and standalone sub-labels, including `(a)`, `(b)`, `(i)`, `(ii)`.
2. **Deduplicate:** retain the first occurrence of an identical source URL/path.
3. **Pair and confirm:** associate each image with the nearest sub-label;
   assign sequential letters only when labels are absent. Raw Markdown order
   can be wrong: confirm figure ownership and panel content/order against the
   source PDF or native contact-sheet inspection. Do not guess ambiguous panels.
4. **Lay out:** each `.figure-row` holds exactly two `<figure>` panels. Use
   `N//2` rows plus one standalone `<figure>` for odd N; a single panel uses a
   standalone figure.
5. **Caption:** one unified `<figcaption>` follows the last row/standalone panel,
   outside the individual figures. List all panels as half-width `(a) ...;
   (b) ...; (c) ...`, separated by `;`, `；`, or `：`. Do not merge `(b)(d)` or
   use full-width `（a）`; absorb standalone labels into captions. Copy any
   required caption styling from the selected template.
6. **Audit:** source unique-image count and identity must match the HTML content
   images (exclude the lightbox's `#lb-img`). Every `图 N` caption needs an
   in-body `图 N` citation, and every body reference needs a matching figure.

Every content image has `loading="lazy"`, meaningful alt text, and the shared
lightbox `onclick` and SVG-fallback `onerror` attributes below. Both locked
templates use `#lb-img` and `#lightbox`; the bilingual template has no content
image example, so use this one in either mode. Replace `IMAGE_URI` with the
resolved image and adjust the alt text, preserving the two event attributes.

```html
<img src="IMAGE_URI" alt="Fig 1a" loading="lazy"
     onclick="document.getElementById('lb-img').src=this.src;document.getElementById('lightbox').classList.add('active')"
     onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22300%22%3E%3Crect width=%22400%22 height=%22300%22 fill=%22%23f5f2eb%22/%3E%3Ctext x=%22200%22 y=%22150%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2214%22%3EFigure unavailable%3C/text%3E%3C/svg%3E'">
```

Retain the selected template's lightbox and back-to-top controls.
A fallback indicates a load failure, not successful source-image verification.
For a single composite image, describe its subpanels without a semicolon-delimited
`(a); (b)` unified-caption pattern when the report verifier would otherwise
count it as multiple figure-row panels. Bilingual captions additionally preserve
English source captions as specified in [bilingual.md](bilingual.md).

### Local images and optional online copies

Default to embedded `data:image/...;base64,...` images for a single-file page.
The one root [../embed_base64.py](../embed_base64.py) serves both modes:

```text
python embed_base64.py "<output.html>" --images-dir "<registered-raw-images-dir>"
```

It resolves GitHub raw URLs by image filename and local paths relative to the
HTML version directory, then the supplied images directory. It is idempotent,
preserves image attributes, and skips existing data URIs. Missing local images
retain their reference and return exit 1; `--allow-missing` is an explicit
degraded result, not a clean completion. Never ship unresolved `images/...`
references. CDN availability does not prove that an image matches the source.

Only when the user requests an online/archive copy, use the root
[../link_images.py](../link_images.py) to rewrite local Markdown references to
the already-authorized hosted image prefix:

```text
python link_images.py "<input.md>" "<BASE_URL-ending-in-images>" -o "<linked-output.md>"
```

This helper rewrites URLs only; it neither uploads nor embeds images. Publishing
still needs the user's authorization. Do not create a bilingual copy of it.

### Native panel-order verification

For suspect split figures, use the available adjacent pdf2md helper to produce
contact sheets and its mapping template, then inspect them with the primary
multimodal model inherited from the current session. Optional helpers inherit
that same model and inspect only assigned figures:

```text
python ../pdf2md/fig_verify.py "<registered-raw-dir>" "<output.html>" --dump
python ../pdf2md/fig_verify.py "<registered-raw-dir>" "<output.html>" --apply "<mapping.json>"
```

Use the helper's generated mapping format, fill only supported judgments, and
leave undecidable figures unchanged and marked unverified. Applying a mapping
may materialize registered fixed input copies while preserving originals.
Re-resolve the source through MANIFEST and rerun the selected HTML verifier
after any correction. No external image-analysis service is required.

## Formulas and tables

Each `.math-block` has a following `<p class="math-note">` explaining physical
meaning in Chinese. Preserve inline `$...$` math. Copy the selected template's
synchronous MathJax 3 setup: `displayMath` needs **both** `$$...$$` and
`\[...\]` delimiters; configuring only one replaces the defaults. Never add
`async`. Keep report line-breaking configuration. **Numbering is mode-specific:**
follow [report.md](report.md#equations) or [bilingual.md](bilingual.md#equations),
not a shared renumbering rule.

Keep every source table, original table number, units, parameter names, and
values; clearly distinguish any added synthesis from original data. Use the
selected template's table styling without improvised cell styles. Retain
LaTeX in cells for MathJax. Detailed caption and transcription rules differ
by mode and are in the respective references.
Place the table immediately after the paragraph explaining its conditions or
comparison and citing `表 N`. Parameter headings state meaning and units and
may carry `.term` triggers. Use a horizontal-overflow wrapper for wide tables.

## Content audit and structural gate

Re-read source and output rather than relying on memory. Verify:

- Keywords (in the header), source headings, all figures/panels, formulas, and
  tables; apply the chosen mode's paragraph/section contract.
- Acknowledgements/funding (including bodies and grant numbers), supporting
  information, conflict-of-interest and data-availability statements, dates,
  cautions/`NOTE:` lines, and all appendix data.
- Complete references, in source order, under `id="refs"` with a ToC link.
  Preserve citation identifiers. For already numbered `[N]` entries, use
  `<ol style="list-style:none;padding-left:0">` so browser numbering does not
  produce `1. [1]`; use ordinary `<ol>` if entries lack numbers.
- Detailed process/profile parameters with their variables and units, rather
  than vague summaries; spot-check 5–10 important numerical values (or all in
  a small source). Explain source-section merges/splits and verify coverage.

Run **only the selected mode's verifier** with the registered Markdown input:

```text
python verify.py "<report.html>" "<source.md>"
python bilingual/verify.py "<bilingual.html>" "<source.md>"
```

Exit 0 is required. Both check math-note counts, MathJax, ToC links, images,
panel captions, figure cross-references, and source back-matter presence.
The report checker requires every display formula to have a unique ordered
tag; the report authoring rule additionally requires sequential numbering.
The bilingual checker adds pairing, color, key-term and insight-structure
checks and permits originally unnumbered formulas with warnings. A verifier
pass is not proof of content fidelity, source-image identity, or rendered math.

## Native visual QA

1. After the structural gate, open the actual versioned HTML in a real browser.
   If `file://` fails, serve its directory with `python -m http.server <port>`
   and use localhost. Resolve images relative to that version directory.
2. Wait for the DOM and MathJax startup/typesetting; scroll through lazy images
   before checking `img.complete && img.naturalWidth > 0` on content images.
   Exclude the empty lightbox image, but do not count an error fallback as a
   source image. Confirm rendered `mjx-container` nodes and absence of raw
   display delimiters or error text; a script tag alone is insufficient.
3. Capture and inspect desktop and narrow/mobile screenshots, including the
   full content or representative sections covering every figure/formula group.
   Check legibility, clipping/overflow, figure order/captions, tables, ToC
   navigation, lightbox open/close, and back-to-top. For bilingual output also
   exercise all language/note toggles, expand/collapse-all, legend, and mobile
   ToC; inspect paired highlights and reference numbering.
   Exercise term hover/focus/tap, Escape/outside dismissal and popup placement
   near viewport edges; inspect figure/table proximity to the explaining prose.
4. Crop/zoom uncertain text or panels and compare with the source PDF/contact
   sheet. Fix the generator/content source, regenerate, rerun the verifier,
   and re-render the affected views until resolved.
5. If browser, screenshots, source panels, or MathJax loading cannot be checked,
   state precisely what remains **unverified**. DOM-only evidence cannot prove
   visual layout. Embedded images work offline, but the locked templates still
   load MathJax from CDN; inaccessible math must be reported as unrendered,
   without silently changing the locked script or claiming a full visual pass.

Locate a working Python interpreter before running commands (`Get-Command
python` / `where python`, then `python --version`). No new packages are needed
for the bundled verifiers or regression suites.
