# Report mode

Use for core interpretation, advisor reports, and ordinary HTML reading notes.
Read [common.md](common.md) first. Template: [../template.html](../template.html).
Verifier/tests: [../verify.py](../verify.py), [../test_verify.py](../test_verify.py).
All commands run from the skill root.

## Interpretation and language

Write a Chinese research-progress report for a graduate student new to this
specific field, with technical depth and physical mechanisms. Interpret the
paper rather than merely restyling Markdown; avoid conversational tutorials,
everyday analogies, or invented claims. Report body paragraphs, lists, and
explanatory table cells are predominantly Chinese. English is retained for
original titles, citation/reference metadata, symbols/units, and first-use
`key-term` annotations. This report-only language rule does not apply to
bilingual `.original-text` or English source captions.

## Header

Fill the locked header in this order, omitting unavailable optional lines/fields:

| Element | Content |
| --- | --- |
| `h1` | Chinese title |
| `.sub` | Verbatim original English title |
| `.cite` | `Author et al. - Journal Year, Vol(Issue): Art#, Affiliation`; only known fields |
| `.journal-info` | Verified indexing/quartile badges and IF, separate from `.cite` |
| `.meta` | Clickable DOI, then 收稿 / 接收 / 出版 dates, separated by ` \| `; omit if none |
| `.keywords` | Source keywords translated with English term annotations; omit if absent |

Do not relocate keywords to the abstract. The template already styles long
DOI links, badges, and IF values. Example badge content (replace with verified
values): `<span class="badge badge-scie">SCIE Q2</span> IF=<span
class="if-val">2.5</span> <span class="badge badge-ei">EI</span>`.

### Journal lookup

Use the available `onescholar` skill first for JCR quartile, IF, CAS, and EI.
If it has no result or is unreachable, try letpub.com.cn; publisher official
pages are the next source for newer/ESCI journals. Use the latest available
JCR year and identify it; do not hardcode an old year. After two unsuccessful
lookup attempts, show `查证中（unverified）` rather than a guessed quartile/IF.

Indexing identity, JCR quartile/IF, and EI status are independent. Read both
the indexing badge and indexing row on LetPub. Its missing EI row is not proof
of non-EI: confirm EI via OneScholar/scigreat's `ei` field, or omit the badge
without asserting absence. Use `badge-scie` for SCIE (SSCI text when applicable),
`badge-esci` for ESCI, and `badge-ei` for confirmed EI. A confirmed SCIE journal
outside JCR uses a plain `SCIE` badge plus `（不在 JCR 收录，无 IF）`, without a
quartile. A delisted journal must not receive a current SCIE badge. Conferences
use `badge-delisted` with `会议论文`; omit the indexing line for confirmed
nonindexed publications. Do not turn a failed lookup into a negative indexing
claim.

## Sections and insights

Map source major/minor sections to h2/h3 and retain all substantive material.
The normal report sequence is research abstract (`abs`, bullet summary plus
one insight), introduction, methods, results/discussion, numbered conclusions,
and key takeaways (`sum`, at most seven). Retain source back matter and
appendix tables (`app`) and add their ToC entries. IDs may follow the existing
`s1`, `s2`, `s2a` pattern; every headed section needs its sidebar link.

Place at least one `.insight` per major h2 section, immediately after the
concept it explains instead of clustering at the end. Use the template's
`.label` (`Note`, or `术语速览` for a short term list). Address one concept per
box, its physical mechanism and practical research relevance. Preserve first-use
Chinese/English term annotations; subsequent occurrences normally use Chinese.

## Equations

The report template uses `tags: 'none'` and retains its line-breaking options.
**Every display formula gets an explicit tag, sequential across this report:**

```html
<div class="math-block">$$ q = h (T_s - T_a) \tag{1} $$</div>
<p class="math-note"><strong>解读：</strong>对流热流密度由换热系数与温差共同决定。</p>
```

Use unique `\tag{1}`, `\tag{2}`, …; when inserting an equation, update later
tags and report cross-references. Check sequentiality during content audit:
the existing verifier rejects missing/duplicate/unordered tags, but does not
prove that numeric tags have no gaps. Do not apply bilingual source-number
preservation or unnumbered-derivation allowances to report output.

## Tables

- **Original source tables:** retain the source number in `表 N. 中文标题`
  (optionally `（原文 Table N）`) inside `<caption>`; preserve data, units, and
  parameters. Use the template's `<thead>`/`<tbody>` structure.
- **Added synthesis:** label `整理表 A.`, `整理表 B.`, … with provenance such as
  `（据原文第 X 节整理）`. Never use numbered `表 N` for an invented summary table.
  If the source has no numbered tables, all report-created tables are 整理表.
- Use the locked table styling, without new inline table styles.

## Gate and delivery

```text
python verify.py "<report.html>" "<registered-source.md>"
python -B test_verify.py
```

Require verifier exit 0, finish the common content audit and native visual QA,
and report any missing project artifacts or unverified rendering. Do not run
the bilingual checker against a report: pairing, colors, and `.insight-note`
are bilingual-only requirements.
