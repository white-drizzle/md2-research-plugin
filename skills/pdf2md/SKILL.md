---
name: pdf2md
description: Use when the user provides a PDF paper (or URL) and wants Markdown with local images for the registered md2htmlnote or md2pptnote pipeline. Triggers on PDF转md, PDF转Markdown, MinerU解析, pdf2md, and PDF阅读笔记第一步.
---

# PDF to Markdown with Shared Raw Outputs (pdf2md)

## Overview

Convert a PDF paper into the MANIFEST-registered shared raw inputs for the literature-note
pipeline: `full.md`, `images/`, optional `fig_health.md`, and the canonical `linked.md`.
The default `linked.md` embeds images as base64 for a self-contained downstream handoff;
GitHub raw URLs are optional for online sharing only. This skill does not generate or
prescribe final HTML or deck locations.

## Runtime and plugin paths

Commands run from this skill's directory inside `skills/pdf2md/`. Locate a working
Python interpreter first (`Get-Command python` / `where python`, then
`python --version`). Quote paths and use syntax appropriate to the current shell.
The SDK fallback needs an already prepared `mineru-open-sdk` runtime and a configured
token; local figure checks need Pillow. This plugin adds no MCP server.

Use the inherited primary model for native figure inspection. Optional helpers
must be bounded and inherit that model; no external vision service is required.
Paper artifacts stay in the user's selected project/output or archive target.
These instructions authorize no automatic commit, push, upload, or publication.

## When to Use

- User drops a PDF and says "转成md" / "解析PDF" / "pdf2md" / "把PDF处理成md给笔记用"
- User has a batch of PDFs to feed into the md2htmlnote / md2pptnote pipeline
- User needs local images and a self-contained downstream input instead of expiring CDN links

## Pipeline Step-by-Step

### Step 0: Work in `_tmp/P<n>/raw/` (project rule)

The PDF parser owns only the shared raw input boundary registered in `_tmp/MANIFEST.json`:
`_tmp/P<n>/raw/full.md`, `_tmp/P<n>/raw/linked.md`, `raw/images/`, `raw/fig_health.md`
(when the health check is run), and the optional corrected copies `raw/full_fixed.md` /
`raw/linked_fixed.md` (2026-09-13 convention: originals are **never overwritten**; fixed
copies exist only for papers with verified figure corrections and are registered in
MANIFEST as `full_fixed_md` / `linked_fixed_md`). Keep parser scripts/logs outside the
paper artifact directories. Do not prescribe or create final HTML or deck locations here;
downstream skills own their versioned output directories. `raw/linked.md` is the canonical
shared downstream input and must remain in `raw/`; downstream resolution rule =
`linked_fixed_md` if registered, else `linked_md` (never decide by file existence alone).

### Step 1: Parse the PDF with MinerU (precision mode)

You MUST end up with a local `full.md` + an `images/` subdirectory whose paths are
**relative** (`![](images/xxxx.jpg)`). Two ways to get there:

**Primary — MCP `parse_documents` (in-session, token pre-configured):**

The `output_dir` value MUST be the exact MANIFEST-resolved raw directory for this paper —
`<project>/_tmp/P<n>/raw` — never an arbitrary batch-name directory. Pass `output_dir` so results are
saved locally. In every command below, `<output_dir>` means this same MANIFEST-resolved
`_tmp/P<n>/raw/` directory (not a project-root or arbitrary batch directory):

```
mcp__mineru__parse_documents(
  file_sources: ["<绝对路径>\\paper.pdf"],   # or {"source": "...", "pages": "1-20"}
  language: "ch",                            # omit if unsure; server defaults to ch
  output_dir: "<project>/_tmp/P<n>/raw"       # resolve P<n>/raw from _tmp/MANIFEST.json
)
```

Precision mode (token present) supports up to 600 pages and returns `full.md` + `images/`
with **local relative paths** (no CDN). If the server instead returns a zip / inline result,
download or extract it into `output_dir` and **normalize**: you must have exactly
`<output_dir>/full.md` and `<output_dir>/images/`.

**Fallback — SDK script (when the MCP server is not loaded):**

Use the bundled `extract_pdf.py` with an already prepared `mineru-open-sdk`
runtime and token supplied through the environment (cmd example):

```bash
set "MINERU_TOKEN=sk-..."
python extract_pdf.py "<PDF绝对路径>" "<MANIFEST-resolved _tmp/P<n>/raw/目录>"
```

The second argument is always the existing MANIFEST-resolved `_tmp/P<n>/raw/` directory for
that paper; do not pass an arbitrary batch-name or project-root output directory.

It calls `MinerU(token).extract(pdf, model="pipeline", language="ch", timeout=600)` then
`result.save_markdown(full.md, with_images=True)`, printing `state=done` on success.

**批量 + 后台（多篇时推荐）：** 用同目录 `run_extract.py` 一次提交多篇，并行解析
（默认 2 并发，避免云端限流），已解析过的自动跳过（缓存）：

```bash
python run_extract.py "<project>/_tmp" "P3-xxx.pdf" "P4-xxx.pdf" ... [--workers 2]
```

`run_extract.py` does **not** read MANIFEST. It extracts `P<n>` from a PDF filename
matching `P<n>-...pdf` or `P<n>_...pdf` and writes `<out_root>/P<n>/raw/`.
Before invoking it, resolve the existing paper entry, pass `<project>/_tmp`, and
confirm that each filename's P-number matches its registered raw directory.
Register a new paper first; do not let filenames allocate identities. When a
registered destination differs, use `extract_pdf.py <pdf> <resolved-raw-dir>` instead.
The runner does not create or update registry entries. `full.md` alone is its cache
key, so verify `images/` after both a parse and a cache hit.
每篇输出 `<project>/_tmp/P<n>/raw/`（full.md + images/），stdout 打印逐篇状态
(done/skip/fail)，exit 0 当且仅当无 fail。token 自动获取（按优先级探测，无需手动 set）：
1. 环境变量 `MINERU_TOKEN`
2. `~/.claude.json` → `mcpServers.mineru.env.MINERU_API_TOKEN`
3. `~/.zcode/cli/config.json` → `plugins.options.super-research-plugin@super-research-plugin.mineru_api_token`
   （已有 Zcode 配置的兼容读取；显式
   `mcp.servers.mineru.env.MINERU_API_TOKEN` 也兼容兜底，不要求安装该插件）
**在支持后台任务的 harness 中把整条解析放后台跑**
（如 Zcode 的 Bash run_in_background），解析期间对话不阻塞，完成后收到通知
再继续 Step 2–4——单篇 3–6 分钟的云端等待不再占用交互时间。

**Flash mode (no token)** only returns CDN links and is capped at 20 pages — NOT suitable
for this pipeline. If the token is missing/expired, stop and ask the user for a fresh
`sk-` token (JWT tokens expire; the current format is `sk-...`).

**After parse, verify the shape before continuing:**

```bash
dir /b "<output_dir>"      # must show full.md AND images/
```

**拆图健康检查（自动）**：`run_extract.py` 解析成功后自动跑 `fig_health.py`，
产出 `raw/fig_health.md`（图注子图数 vs 图片链接数比对，MinerU 乱序/分割不全
检出）。图注行前缀 `Figure N.` 与 `Fig. N.` 均被识别。出现「疑似」行（如 Fig7 链接数 ≠ 图注数）
时：先看报告原因——**MinerU 常把多面板图合并成一张大图**（图注 3 子图但仅 1 张图
链接，可能正常），需检查实际图片和源图确认；确系缺图
才需处理。`python fig_verify.py <raw> [<html>]` 默认输出带编号接触表与空映射模板，
`--dump` 与默认行为相同。主模型读取接触表，结合原文图注填写单字母角标；
合并图或无法判断的面板留空或填 `?`。只有显式执行
`python fig_verify.py <raw> [<html>] --apply <mapping.json>` 才应用已核验的映射。
此流程不调用外部视觉 API。未填角标的模板返回失败并保持输入不变。
无可判定的面板保持原样并标注。纠正除重写 HTML 外，
同步物化修正版输入链（2026-09-13）：按同一映射重排 `raw/full_fixed.md` 的图链接
→ 生成 `raw/linked_fixed.md`（base64）→ 幂等更新 MANIFEST 的 `full_fixed_md` /
`linked_fixed_md`；原件 `full.md`/`linked.md` 保持不变。

### Step 2: Generate `linked.md` — base64 embed (default, self-contained) or GitHub raw (optional)

**主路径（推荐，2026-08-16 起）：base64 内嵌，完全自包含，不依赖任何外部网络。**

```bash
python link_images.py "<output_dir>/full.md" "<output_dir>/images" --embed -o "<output_dir>/linked.md"
```

Every `![](images/xxxx.jpg)` → `![](data:image/jpeg;base64,...)`. The output must be
`<project>/_tmp/P<n>/raw/linked.md`; `raw/linked.md` is the single shared downstream input.
Expected output: `replaced: N relative image refs (embed)` and `leftover relative refs: 0` (exit 0).
缺本地图时保留原引用并计入 leftover（exit 1）——门控语义与 URL 模式一致。

**Optional local archive:** only when the user selects an archive target, the
existing staging helper can copy `full.md` and `images/` into its fixed local
`reading-notes/<slug>/` subdirectory:

```text
python stage_to_repo.py "<output_dir>" "<user-selected-archive-root>" "<user-selected-slug>"
```

This copies files locally; it does not publish. It replaces an existing target's
`images/` directory, so use a new slug or obtain explicit replacement authority.
No repository, branch, credentials, or standing push authorization is supplied by
this skill. A remote upload/publication requires a separate explicit user request
and the user's chosen destination.

### Step 3: Optional hosted image URLs

Only when the user explicitly chooses hosted images and supplies their hosted
prefix, use URL mode instead of embedding:

```text
python link_images.py "<output_dir>/full.md" "<user-selected-BASE_URL-ending-in-images>" -o "<output_dir>/linked.md"
```

`BASE_URL` includes `images`; the script appends `/<filename>`. This command only
rewrites links. It uploads nothing and leaves absolute URLs untouched. Check any
remaining relative references before downstream authoring.

### Step 4: Verify integrity (MANDATORY gate)

```bash
rg -c "!\[" "<output_dir>/full.md"                 # total image refs in source
rg -c "data:image" "<output_dir>/linked.md"          # embed 模式: must equal the count above
rg -c "\(images/" "<output_dir>/linked.md"          # must be 0 (no output, exit 1)
```

- Embed 模式：linked.md 中每个 `![](images/...)` 都必须是 `data:image/...;base64,` 前缀。
- Zero remaining `(images/...` relative refs。
- 用户选择 hosted URL 时，改为核对该前缀的图片引用数及可达性；本地归档则核对目标图片与源图一致。

### Step 5: Handoff to the md2 series

The output `linked.md` is the source for any downstream skill:

| Skill | Use case |
|-------|----------|
| `md2htmlnote` | 中文解读或逐段双语精读 HTML，按请求选择模式，直接消费登记的 linked 输入 |
| `md2pptnote` | 中文文献汇报 PPTX，消费同一登记的 linked 输入 |

Copying `linked.md` next to the source PDF is a legacy convenience only; the canonical shared
input remains `_tmp/P<n>/raw/linked.md` as registered in MANIFEST. Invoke downstream skills
with the MANIFEST-resolved path.

## File Layout

```
skills/pdf2md/
├── SKILL.md          # this file
├── extract_pdf.py    # SDK fallback parser (mineru-open-sdk)
├── link_images.py    # relative-path → base64 embed (默认) / GitHub raw URL (可选)
└── stage_to_repo.py  # local copy into a user-selected reading-notes archive
```

The sibling `../md2htmlnote/` supplies HTML authoring; `../md2pptnote/` supplies
decks. Each skill keeps its own existing image helper. For a new project, start
with [the registered synthetic example](../../examples/registered-paper/README.md).

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using flash mode (no token) → CDN links + 20-page cap | Use precision mode (token present) — CDN links expire in 1 month, defeating the purpose |
| Old JWT `eyJ...` token expired (401 Unauthorized) | Ask user for a fresh `sk-...` token (current format) |
| run_extract.py 报"找不到 MinerU token"，但插件 userConfig 已填 | zcode 的 token 在 `~/.zcode/cli/config.json` → `plugins.options.super-research-plugin@super-research-plugin.mineru_api_token`（**不是** `mcp.servers`，2026-08-16 实测踩坑）；确认 load_token 三源探测路径齐全 |
| 图注是 `Fig. N.` 前缀（非 `Figure N.`）→ fig_health 报"有图无图注" | fig_health.py 的 CAP_RE 已兼容 `Figure|Fig` 两种前缀；若再出现未归属，先查图注行格式再改正则 |
| Images referenced as `images/images/xx.jpg` (double prefix) | The regex captures only the filename after `images/` — do NOT include `images` twice in BASE_URL |
| `linked.md` still contains `(images/...` refs | Step 4 grep must be 0 — re-run link_images.py or fix the pattern |
| 网络不可达（raw.githubusercontent.com / jsdelivr CDN curl 000） | 走 embed 主路径（`--embed`）生成自包含 linked.md；GitHub raw 方案已废弃为主路径，仅分享用 |
| Parse output is a zip / inline blob instead of full.md + images/ | Normalize: extract into `output_dir`; you MUST have `full.md` + `images/` before Step 2 |
| P-number does not match the project | Resolve the existing MANIFEST entry before naming a batch input |
| Intermediates mixed with the user's paper files | Keep all scripts/outputs under `_tmp/` (project rule) |
| Referenced image missing from the selected archive | Compare local source and destination images before delivery |

## Production Checklist

- [ ] MinerU parse succeeded in **precision mode** (state=done), output has `full.md` + `images/`
- [ ] `link_images.py --embed` ran with exit 0 (`leftover relative refs: 0`) → linked.md 自包含
- [ ] Every `![...](...)` in `linked.md` is a `data:image/...;base64,` URI (grep counts match)
- [ ] Zero `(images/` relative refs remain
- [ ] 若用户要求本地归档，已核对其明确选择的目标；无自动发布
- [ ] `linked.md` handed off to `md2htmlnote` (or another md2 skill) — output delivered

## The Checkpoint Rule

Never claim completion from memory — run Step 4's greps, then (if a downstream skill is
invoked) visually verify in the browser that the images actually render. Embed 模式
离线即可验证（本地打开 HTML）；GitHub 分享路径需网络可达时才能验证 raw URL。

## 统一路径规范（项目级，强制）

机器可读路径真相源是用户项目的 `_tmp/MANIFEST.json`；项目已有布局规范时同时遵循。
本 skill 只负责共享 raw 输入，登记示例见
[examples/registered-paper](../../examples/registered-paper/README.md)。

- 读取/写入 MANIFEST 登记的 `_tmp/P<n>/raw/`：`full.md`、`linked.md`、`images/`、`fig_health.md`。
  已核验纠正按需生成 `full_fixed.md`/`linked_fixed.md`，登记为 `full_fixed_md`/`linked_fixed_md`，原件保持不变。
- 下游输入优先使用 **已登记** 的 `linked_fixed_md`，否则使用 `linked_md`；不按文件存在与否决定。
- HTML 与 deck 由各自 sibling skill 写入登记的独立版本目录；旧 flat 布局只用于识别历史产物。
- 项目已有 `_tmp/scripts/pipeline_layout.py` / `check_image_refs.py` 时运行它们；这些项目工具不随插件提供。
  无这些工具时仍需核对登记路径、current/version 关联和图片内容；不要另建注册框架。
