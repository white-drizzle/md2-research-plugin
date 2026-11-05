# Minimal registered paper project

This is a synthetic local fixture, not a published paper. Its invented values
and image demonstrate paths only; there is no PDF, DOI, API call, or upload.
The bundled `full.md`, local PNG, and base64 `linked.md` are self-contained.

`_tmp/MANIFEST.json` uses the existing `papers[]` contract. Paths are relative
to this project directory. HTML and deck have separate `current` files and
`versions[]` ID spaces. The version directories are reserved placeholders;
both `current_version` values are `null` because no finished artifact exists.
Do not interpret a placeholder as a verifier or visual-QA pass. Existing
projects may retain additional metadata; do not replace their whole MANIFEST
with this example.

To start a new registered paper:

1. Copy this directory to the local project/output target explicitly selected
   by the user. In an existing project, add a paper entry using its existing
   registration procedure instead of overwriting its registry.
2. Select an unused project P-number. Rename `P1/` and update the entry's `id`
   and every registered path together. Reserve independent HTML/deck version
   IDs and matching directories. Keep `current_version: null` until an
   artifact is ready.
3. Replace the synthetic raw inputs with the paper's local `full.md` and
   `images/`. From this plugin's `skills/pdf2md/` directory, run:

   ```text
   python link_images.py "<project>/_tmp/P<n>/raw/full.md" "<project>/_tmp/P<n>/raw/images" --embed -o "<project>/_tmp/P<n>/raw/linked.md"
   python fig_health.py "<project>/_tmp/P<n>/raw"
   ```

   For an authorized PDF parse, `extract_pdf.py` accepts the resolved raw
   directory directly. The batch `run_extract.py` does not read MANIFEST:
   filename `P<n>-title.pdf` or `P<n>_title.pdf` must already match the entry,
   and its output root must be `<project>/_tmp`. Register first, then parse.
4. Invoke `md2htmlnote` in report or explicit bilingual mode, or `md2pptnote`,
   using this project and the registered linked source. Fill the reserved
   version directory, run that skill's existing gates and native visual QA,
   then set its current pointer to the registered version ID. Use
   `linked_fixed_md` only when registered by a verified figure correction;
   the mere existence of a fixed file is insufficient.

The HTML placeholder names `P1_synthetic_2026.html`; rename that output path
with the new paper. The deck placeholder lists its existing artifact names.
No registry manager or project-specific layout checker is bundled here.
Publishing or pushing paper artifacts requires a separate explicit user
request and destination.

## Try the four-view reader

Run this command from the repository root. It packages the small reader,
the synthetic paper graph, two calculation steps and two layered topics.
The existing registered PNG is embedded in the result.

```text
python skills/md2htmlnote/build_multiview.py examples/registered-paper/reader-example.html examples/registered-paper/guide-example.json -o signal-note.html
```

Open `signal-note.html`, select an evidence node and follow its reader link.
Use the return control to resume the same view. Use the full report or
bilingual template for a research paper.
