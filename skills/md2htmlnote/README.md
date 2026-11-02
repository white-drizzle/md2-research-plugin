# md2htmlnote

Convert MinerU-exported academic Markdown into a source-grounded HTML reading
page. The single entry supports two modes:

| Mode | Use | Distinct behavior |
| --- | --- | --- |
| **report** (default) | Core interpretation / advisor study report | Chinese technical prose, `.insight` boxes, sequential explicit equation tags |
| **bilingual** (explicit) | Full parallel reading / 对照翻译 / semantic colors | Complete EN/ZH paragraph pairs, paragraph colors and paired inline highlights, deep analysis and personal reflection, language/note toggles, original equation tags |

Both preserve source figures, tables, formulas, references, and back matter;
provide ToC navigation and a lightbox; and use separate locked templates and
verifiers. Embedded images work offline. MathJax 3 is loaded from CDN and
requires network access for rendered formulas.

## Invoke

In Codex, use a prompt such as:

```text
Use $md2htmlnote for a report from the MANIFEST-registered paper source.
Use $md2htmlnote in bilingual mode for full English/Chinese parallel reading with semantic colors.
```

A legacy slash-command harness can use `/md2htmlnote <source.md>` and add an
explicit bilingual request. Mode selection is an instruction to the authoring
agent, not a Python CLI flag. See [SKILL.md](SKILL.md) for routing, then
[references/common.md](references/common.md) and only the selected mode guide.

## Resource layout

```text
md2htmlnote/
  SKILL.md
  references/common.md
  references/report.md
  references/bilingual.md
  template.html              report template (locked)
  verify.py                  report gate
  test_verify.py             report regression suite
  bilingual/template.html    bilingual template (locked)
  bilingual/verify.py         bilingual gate
  bilingual/test_verify.py    bilingual regression suite
  link_images.py             shared local-Markdown-to-hosted-URL helper
  embed_base64.py            shared HTML image embedding helper
```

Copy CSS, skeleton, controls, and JavaScript from the selected template exactly;
fill content slots only. Never mix mode-specific formula rules or verifiers.

## Commands

Run from the **md2htmlnote skill root** with a working Python 3 interpreter.
These helpers and suites use only the standard library; no package installation
is needed. Replace bracketed arguments with resolved paths.

```text
python verify.py "<report.html>" "<source.md>"
python bilingual/verify.py "<bilingual.html>" "<source.md>"
python -B test_verify.py
python -B bilingual/test_verify.py
python embed_base64.py "<output.html>" --images-dir "<registered-raw-images-dir>"
python link_images.py "<input.md>" "<BASE_URL-ending-in-images>" -o "<linked-output.md>"
```

Use only the matching verifier for each output; exit 0 is the structural gate.
The report suite includes one project-dependent P1 regression which skips if
its `_tmp/MANIFEST.json`/artifact fixture is unavailable. Bilingual source
unnumbered derivations may produce a warning while still passing.

`link_images.py` rewrites URLs; it does not upload or embed. Prefer
`embed_base64.py` for local images. Online publication is optional and must be
requested. Use the same root helpers for both modes.

## Pipeline and delivery

Resolve inputs through `_tmp/MANIFEST.json`: registered `linked_fixed_md`,
otherwise `linked_md`. Both modes write the registered
`P<n>/html/versions/<html-version>/` artifact. `html/current.json` points to a
registered HTML version or `null`; follow existing project registration tools.

After the source completeness audit and correct verifier pass, open the real
artifact in a browser and perform the [native visual QA](references/common.md#native-visual-qa)
procedure. Check DOM/image/MathJax loading, screenshots, layout and controls;
fix the generation source and re-render uncertain regions. Report unverified
rendering explicitly when browser or resource loading cannot be checked.

## License

MIT
