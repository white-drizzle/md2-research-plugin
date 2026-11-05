# Four-view HTMLnote

The graph, flow and layered reader are different ways into the **same analysis**.
Choose report or bilingual content as usual. Author the full reader first so
the three guides can point to real headings and exhibits.

| View | What the reader gets |
|---|---|
| 文献鸟瞰 | A root, research branches, methods and evidence. Give edges meaningful labels. Use a shared node for a method the paper actually uses in multiple branches. |
| 工艺流程图 | Select a stage to read its input, action, output, role and evidence. For a computational study use the model or data pipeline. For a theory paper or review use its argument or comparison sequence, with an appropriate flow tab title. |
| 分层精读 | Display each conclusion together with its conditions. Put its mechanism in one fold and the measurements, derivation or comparison in an evidence fold. Presets change the depth of all topics. |
| 精读解析 | The complete report or bilingual analysis, including its original figures, tables, glossary and equations. Its element IDs are the guide destinations. |

## Guide data

Start from the [synthetic two-signal guide](../../../examples/registered-paper/guide-example.json).
Replace the content and relationships with facts about the current paper.
The author supplies the claims and evidence in the requested reading language.

| Field | Contents |
|---|---|
| `title, summary` | A concise reading title and a short description of the paper as a whole. Optional `byline` gives authors/date. |
| `flow_label` | Optional navigation label, e.g. `研究流程` or `论证路径`. Defaults to `工艺流程图`. |
| `overview.root` | ID of the single root node. |
| `overview.nodes[]` | Each node contains `id, label, kind, group, summary, detail, anchor`. Kinds are `root, branch, method, evidence, shared`. A branch uses its own ID as its group. Methods and evidence use a branch ID. Use an empty group for root and shared nodes. Keep graph labels short and give a specific fact in the inspector. |
| `overview.edges[]` | Each edge contains `from, to, label`. Connect all nodes to the root through source-grounded relationships. |
| `flow[]` | Each stage contains `title, input, action, output, role, anchor`. Identify background stages and distinguish them from the stages tested by the authors. |
| `depth[]` | Each topic contains `title, condition, conclusion, mechanism, evidence, anchor`. Keep sample sizes, units and comparison groups alongside results. |

An `anchor` is the existing ID of the most relevant paragraph, heading, figure,
table or equation in the reader, without a leading `#`. For images above a
distant target, include intrinsic width and height so lazy loading preserves
the landing position. An optional integer `page` is the PDF file page, starting
at 1. Check page numbers against the actual PDF. Navigation reserves the hash
prefix `view/` for mode selection. Use distinct reader IDs; the builder
reports any collision with the navigation shell before writing the output.

Nodes, stages and topics may each include a `table` with `caption, columns,
rows` and a `figure` with `path, caption`. Image paths resolve relative to the
JSON file and are embedded during assembly. Use original figure/table numbers
in captions and introduce exhibits in the corresponding prose. Each cell
retains its units and its association with the source row.

Use `[[term-key|visible label]]` in guide prose and table cells to reuse an
entry from the full reader's glossary. Write short formulas and units in plain
text or Unicode. Link to longer typeset equations in the reader.

## Build and inspect

From the skill directory, use separate input/output files and the registered
HTML version path:

```text
python build_multiview.py "<reader.html>" "<guides.json>" -o "<registered-note.html>" --pdf "<source.pdf>"
python verify.py "<registered-note.html>" "<registered-source.md>"
```

For bilingual content use `bilingual/verify.py` for the second command.
Omit `--pdf` for a source without a local PDF. The three guides and local
figures travel inside the finished HTML. The PDF link is relative to the
output when possible. A PDF on another Windows drive uses a local file URL.
The full reader retains its MathJax setup.

Open the finished file. Select a graph node and a neighbor, choose a flow stage,
open an individual topic and exercise the depth presets. Follow a source link
and return. Check the selection, scroll position and expanded state, browser
Back/Forward, and a direct reader hash on reload. Inspect a narrow viewport,
the original reader's glossary/lightbox/equations and bilingual language
controls as applicable. Set the registered current pointer after these checks.
