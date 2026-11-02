---
name: md2pptnote
description: 'Convert MinerU-exported markdown files (single or multiple) into a self-explanatory Chinese presentation PPTX for reporting to an advisor or senior colleague who has NOT read the original papers. The output deck has a complete argumentation unit on every slide (claim → evidence → interpretation → figure binding), explains jargon in plain language, and binds every figure to the conclusion it proves. Triggers on: 汇报PPT, 综述PPT, 多篇转PPT, 文献转幻灯片, 文献汇报, make a review PPT.'
---

# Markdown to PPT Reading Note (md2pptnote)

## Overview

从 MinerU 导出的 MD（单篇或多篇）生成面向导师/师兄的汇报 PPTX。核心目标：**听众不用读原文也能看懂每一页在讲什么**。

三大可读性铁律（违反任何一条即返工）：
1. **结论先行**——每页必须先给结论（claim），再给证据/数据，最后给启示（so_what）。禁止“只有数据没有结论”。
2. **名词必解释**——专业名词（Zemax / ADRC / ITAE / Re / IMC…）首次出现必须带一句人话解释。禁止名词堆砌。
3. **图证绑定**——每张图必须声明证明页内哪个结论（figure.bound_to）。禁止“为放图而放图”。

## 研究型默认模式（复杂论文/正式汇报）

复杂模型、算法、优化、多实验或正式组会汇报默认采用：

```text
原文理解 → slide_contract → slide_plan → 渲染
→ 结构/几何校验 → 主模型原生多模态语义 QA → 交付到用户选定位置
```

### 主模型与执行模型分工

- **继承当前会话的主模型**：读取原文、确定论文主线和页序；为每页写唯一主旨、听众问题、输入/处理/输出、桥接、必须/禁止内容和证据边界；审查子模型输出；直接读取渲染后的 PPT/PDF/PNG 做默认视觉与语义 QA。
- **可选的同模型 helper**：仅在运行环境允许且确有独立工作时使用，继承主模型，分配有界任务。只按 `slide_contract.json` 填充 `slide_plan.json`，整理表格/公式/图注并执行机械校验；不得自行重排页序、合并/拆分页面或新增科学结论。
- **原生视觉检查**：主模型直接检查页图；可选的同模型 helper 只做有界复核。无法读取的素材明确标为未核验，数值仍以原文/源码/像素证据为准。

### slide_contract 规划层

`slide_contract.json` 位于原文理解和 `slide_plan.json` 之间，回答“为什么这样讲”，而 `slide_plan.json` 回答“如何渲染”。规范见 `slides/slide_contract_schema.md`。

每页至少锁定：

- `one_sentence_message`：页面唯一主旨；
- `audience_question`：页面回答的听众问题；
- `must_show` / `must_not_show`：内容边界；
- `evidence`：原文行号、图表或数据来源；
- `section`：单行短章节标签；
- 推荐补充 `input` / `process` / `output`、`bridge_from_previous` / `bridge_to_next`、`scientific_caveat`。

生成或修改 `slide_plan.json` 前先运行：

```bash
python verify_contract.py slide_contract.json slide_plan.json
```

contract 只做结构和身份一致性校验；“页面是否真的讲清楚”由后续语义 QA 判断，不用脆弱正则代替科学判断。

### 研究型页面硬规则

1. 每页只能有一个核心结论；无法用一句话复述时，优先拆页或删内容。
2. 明确区分环境输入、模型响应、优化器、候选解集和最终输出。
3. 公式必须说明角色：起点、化简过程、核心计算公式或评价指标。
4. 优化论文必须区分决策变量、目标函数、约束、Pareto/候选解集和最终选点。
5. “最优、显著、接近、工程可用”等措辞必须有 `evidence` 支撑；Pareto 折中不得写成两个单目标同时最优。
6. 章节标签默认使用单行短文本（如 `02 · 温度场与 PCB 响应`），不要把完整解释句塞进页眉。

## 流程（五阶段）

### 阶段① 扫描输入
- 从项目 `_tmp/MANIFEST.json` 解析用户选择的论文和已登记 linked 输入；多篇保持其已登记 P-number，不按文件排序重新分配身份
- 提取每篇：标题、期刊/年份/DOI、核心方法、关键数据、图注

### 阶段② 框架澄清
- 若存在已有综述框架（`sections.json` + `sections/*.html`，或综述 HTML），**必须先问用户**：采纳现有框架 / 重新生成 / 优化后使用
- 若只给了原始 MD 无框架，跳过此步直接提炼

### 阶段③ 主模型规划：原文 → slide_contract.json

复杂科研论文先由主模型完成论文理解和叙事决策，再允许执行模型生成 `slide_plan.json`：

1. 抽取论文中心问题、方法链、输入/处理/输出和最终工程结论；
2. 按“问题 → 建模 → 验证 → 优化 → 结果”的实际因果关系决定页序，不机械照搬论文目录；
3. 为每页写 `one_sentence_message`、`audience_question`、`must_show`、`must_not_show` 和 `evidence`；
4. 给模型串联页补 `bridge_from_previous` / `bridge_to_next`，明确上一页为什么导向下一页；
5. 标注论文信息缺口、根据表格反推的变量和不应过度解读的结论；
6. 运行 `python verify_contract.py slide_contract.json slide_plan.json`，通过后冻结 contract；
7. 将 contract 和字段边界作为自包含 prompt 交给执行模型，执行模型不得自行改页序或新增科学结论。

主模型应优先完成这一步，不能把“论文主线是什么”交给只负责 JSON 填充的执行模型。

### 阶段④ 提炼论证单元 → slide_plan.json
- 逐篇读 MD，按 `slides/argument_rules.md` 提炼论证单元
- 按 `slides/json_schema.md` 填 JSON：每页一个 slide 对象，`body` 用类型化元素（point/qa/note/ced）
- 三种论证形式（point 结论前置 / qa 问答叙事 / ced Claim-Evidence-Data）**由 agent 自行判断哪个最适合当前部分**，不强制统一
- **先跑图组提取器**：`python extract_figures.py <paper.md>` 输出每个 Figure 的图组清单（图片链接 + 图注 + 子图标签 + 漏图警告），**据此选图、填 panels、写 source**。禁止裸读 MD 凭感觉挑图
- 选图：按 `slides/layouts.md` 选用准则，从图组清单提取关键图（跳过 <150px 占位图）。将图片下载到当前 `output` 目录下的 `assets/figures/`；其中 `output` **始终是** MANIFEST-resolved
  `_tmp/P<n>/deck/versions/<deck-version>/`，不是项目根目录或任意自建目录。
- **多面板图收集协议（MinerU 拆分问题，必读）**：MinerU 会把一张完整图（如 `Figure 7a–e`）拆成**多个连续 CDN 图片链接 + 末尾统一图注**。提炼时必须：
  1. **收集**：在图组清单里收集该 Figure 的**全部**链接和子图标签（`(a)`/`(b)`），禁止只挑最后一张或第一张
  2. **去重**：同一 URL 出现多次只保留第一张
  3. **配对**：按图组清单的标签顺序与 MD 图注里的 a–f 配对（无标签则按顺序 a,b,c…）
  4. **按需挑选**：不必把所有子图都放上。**只选与页内结论直接相关、或需要重点解释的子图**（如 Figure 7a–e 中只选最关键的 b/c/d），信息量低或无关的面板剔除，在 speaker notes 提一句即可。图注对应不上 = 图文弱关联（病症 3），必须根治
  5. **填 panels**：选中的子图填进 `figure.panels`（`{path, label}`），`subcaptions` 只描述选中的面板
  6. **选 layout**：多面板图用 `multi_figure`（栅格）；**面板数越少每张越清晰**，宁可精选 2-3 张也不堆 6-7 张

**图号归属铁律（防漏图错位）**：图片链接归属它**后面最近的 Figure caption 的编号**，绝不按"图片组顺序序号"对应编号。MinerU 可能漏图（caption 在、图链接缺），遇到 `[疑似漏图]` 警告时：该 Figure 编号仍保留，**后续链接继续归属下一个 caption，绝不错位**。`source` 必须写精确图号 `Fig. N[面板]`（如 `Fig. 6h`、`Fig. 10 (a–c)`），禁止"Fig. 吸收率数据"这类模糊描述。

**图证面板匹配铁律（防"图号对但面板错"）**：图号归属正确 ≠ 面板选对了。同一 Figure 的不同面板**类型可能完全不同**（实例：P5 Fig 6 的 (a)(b) 是光斑灰度图、(c)(d) 是带 Irradiance 坐标轴的辐照度分布图），选错类型观众就从图里读不出论点数值。
1. **面板类型必须与论点匹配**——论点引用具体数值（峰值 mW/mm²、宽度 mm、温差 °C）时，选**能读出该数值的面板类型**（带坐标轴的分布/曲线图），灰度光斑/流场示意类面板对数值结论是弱图证。例：论"辐照度峰值与光斑宽度"，必须选辐照度分布图 (c)(d)，不能选光斑灰度图 (a)(b)。
2. **打标签粒度精确到实际选中的面板**——`source`/`fig_ref`/面板 `label` 必须与图片实际内容一一对应。选中 (c)(d) 就写 `Fig. 6 (c,d)`、面板标 (c)(d)，**禁止沿袭整图图注编号或笼统写 `Fig. 6`**。面板标签 (a)(b)(c)(d) 与图片内容错位 = 图文错配。
3. **归属靠图组清单 + 视觉交叉核验**——用 extract_figures 图组清单定编号，再对图片特征（有无坐标轴/单位、VIM 位置、是灰度图还是曲面图）做视觉核验确认面板类型，双重确认后才填 panels。

**选图与正文衔接铁律（图证双向绑定）**：选图的关联不能只存在 `figure.bound_to` 里——听众看不到。**选图的同时在正文里写衔接**：
- 结论元素（`point.lead` / `qa.question` / `ced.claim`）加 `fig_ref` 声明它由本页哪张图支撑（值用精确图号，如 `6h` / `10 (a–c)`，与 `source` 同规格）
- 渲染时结论句自动加酒红前缀"**如图 xx 所示，**"——先想"这句结论靠哪张图、图里显示什么"，再定 `fig_ref`，把选择决策写进正文

**读图内容铁律（图读法，防"图放上去没人会读"）**：每张选中的图，紧跟其"如图 N 所示"结论元素后写一个 `figread` 元素（body 元素，见 `slides/json_schema.md`），讲清**坐标轴**（横/纵轴单位与范围）、**图例**（颜色/线型/符号含义）、**图意**（图表明什么结论，带关键数值）。听众不看原文也能读懂图。数值必须来自 MD 原文，配图前先经视觉核验图的实际类型（热力图 vs 分布曲线 vs 照片），禁止视觉读数当数值来源。**装饰性示意图/纯照片（无坐标轴/图例可讲）可豁免**。
- **渲染形态（2026-08-10 定稿）**：无"读图"小标题（该词 AI 感强，正式汇报不出现）；只有 `坐标轴：`/`图例：`/`图意：` 三行（有值才渲染）
- **axes 只填真坐标轴图**（曲线/散点/柱状/3D 曲面/热像带数值轴）：写横/纵轴变量与范围。示意图/照片/SEM/显微/云图/等值线/框图/工艺流程等**省略 axes 字段**，内容介绍放 `shows`（图意）；axes 里出现"无坐标轴"类字样 = 残留标记，verify_plan 直接报错

### 阶段⑤ 渲染

下文命令中的 `output/` 是占位符，始终指向 MANIFEST-resolved 的
`_tmp/P<n>/deck/versions/<deck-version>/`（当前 deck 版本目录），不是项目根下或任意
自建的 `output/` 根目录。

- 运行 `python render2pptx.py output/slide_plan.json --out output/final_presentation_cn.pptx`
- 渲染器是纯渲染，不判断内容。排版规范见 `slides/render_rules.md`

### 阶段⑥ 校验 + 反馈回路
1. **contract 校验**（提炼和执行之间）：`python verify_contract.py output/slide_contract.json output/slide_plan.json` —— 检查页面 ID、顺序、章节标签和规划字段一致；失败先修 contract/plan，不渲染
2. **图注一致性校验**（渲染前）：`python verify_plan.py output/slide_plan.json` —— 检查 `source` 精确图号格式、`bound_to` 指向页内结论、图片文件存在、**图证双向绑定**（图必须被正文 `fig_ref` 引用、`fig_ref` 图号与 `source` 一致、无图不引用）。另有**软提醒**（warning 不阻断）：有图但无 `figread` 读图内容 → 提示检查是否漏配（装饰性示意图可豁免）。违规先修 JSON 再渲染
   - **2026-08-16 P10 实测违规形态**：① 本页无 figure 却写 `fig_ref`（图在别页）→ 违规，删掉该 fig_ref；② `claim_figure` 布局的图没被正文引用 → 图证绑定失败——页级 `claim` 不参与绑定检查，需在 body 的 **figread 元素上加 `fig_ref`**（figread 渲染不读 fig_ref，无视觉副作用，仅满足绑定）；③ 单图页的结论元素（point/ced/qa）必须写 `fig_ref`，否则孤儿图违规
3. **结构校验**：`python verify_pptx.py output/final_presentation_cn.pptx`（slide 数/图片数/notes/越界）—— **speaker_note 每页必填**（`ok` 判定 = 0 越界 && 0 缺 notes；P10 实测 12 页全缺 notes 导致 `ok:false`，补齐后通过）；slide_plan 的每一页都要写 `speaker_note`，不要留空
4. **面板一致性检查**：对每个 `multi_figure` 页，确认 `figure.panels` 中**明确选取的面板**已在 `subcaptions`、`source`/`fig_ref` 和 speaker notes（如适用）中有意记录；面板标签、顺序与 MD 源图注及图组清单一致。只有当 contract 明确要求选取该 Figure 的**全部**面板时，才要求选中面板数等于 MD 图注里的完整面板数；若 contract 允许精选子图，不得因未包含全部面板而报错。
5. **主模型原生多模态语义 QA（默认）**：导出 PDF/PNG 后，主模型直接读取页面图片，不看 speaker notes，逐页完成盲读测试：
   - 能否用一句话复述本页主旨？
   - 能否指出本页输入、处理和输出？
   - 能否说明与上一页/下一页的因果连接？
   - 是否出现两个互相竞争的中心、术语未解释或结论超出证据？
   - 是否把环境输入、模型响应、优化器、候选解集和最终输出混为一谈？
   可选同模型 helper 可复核指定页面；无法读取的素材标为未核验，不要求外部视觉服务
6. **视觉排版 QA**：手动 soffice→pdf→pdftoppm 渲染一次，检查标题/章节页眉、公式、图表、文字是否溢出/重叠/截断；主模型具备多模态时优先直接检查，不要无条件调用外部视觉模型
7. **反馈回路**：发现问题 → 改 `output/slide_contract.json` 或 `output/slide_plan.json`（改 JSON 不改 PPTX）→ 重渲 → 重新跑 contract/图注/结构/语义门控
8. 写 `output/qa_report.md`，记录机器门控、语义 QA、视觉修复和未决科学风险

## 输出

每份 deck 必须读取 `_tmp/MANIFEST.json`，并写入登记的版本目录：
`_tmp/P<n>/deck/versions/<deck-version>/`。每个 deck 版本目录包含以下六件套：

```
_tmp/P<n>/deck/versions/<deck-version>/
├── slide_contract.json
├── slide_plan.json
├── final_presentation_cn.pptx
├── qa_report.md
├── asset_manifest.md
├── assets/figures/
└── pages/
```

> `slide_contract.json` 与上述六件套一并保留；下文流程命令中的 `output/` 路径即指
> MANIFEST-resolved deck version directory，不得在其外另建输出目录。

**迭代规则**：同一 deck version 内允许反复就地覆盖 `slide_contract.json`、
`slide_plan.json`、`.pptx` 与 QA 产物。新的 candidate/reviewed milestone 必须创建新的
`<deck-version>`，不得新建 `_v2` 后缀目录或回到旧 flat 布局。版本 ID 与 HTML 版本 ID
独立，不要求相同。

`_tmp/P<n>/deck/current.json` 只承担当前 deck 版本指针职责；`current_version` 必须是
MANIFEST 已登记且实际存在的 deck version ID，或无当前产物时为 JSON `null`，不得为空、
缺省或指向 HTML 版本。

**Legacy reference only**：旧的 `_tmp/<NN>-<deck简称>/` 工作目录及其 `versions/`
快照规则仅用于识别/迁移历史产物，不是新 deck 输出规则。

## 关键约束
- **不得编造**论文里没有的数据/结论。所有数值必须来自 MD 原文
- 图注 + Source 标注（`Source: Fig. X, 期刊 年份` 或 `[P#]` 格式）
- 图片下载失败时用占位提示，不静默丢弃
- 产出真实 `.pptx`，不止是 outline
- 正文标题默认一行；必须换行时最多手动拆成两行，避免标题高度吞掉正文/图表区域
- **full_table 表格上限 10 行数据**（不含表头）；超过必须拆分或改图表页，避免表格字号/行高不可读
- body `type` 必须是 `point/qa/note/ced/figread/formula` 之一；拼写错误不得静默丢弃
- 正式汇报每页 `speaker_note` 必须是非空的一句话（不写演讲稿）

## 标准附加页（封面 / 论文信息页 / 目录页）

2026-08-10 P1 试跑沉淀。每个 deck 默认含 3 页附加页，**正文从 s04 起**：
`s01` 封面（cover）→ `s02` 论文信息页（point_figure + 期刊封面 external 图）→ `s03` 目录（toc）→ 正文 s04…。三页均无 `fig_ref`。

### 封面页（cover layout）
- `title` 34pt 居中；**中文标题 >20 字必须用 `\n` 手动拆两行**（渲染器不自动换行，超长标题会溢出叠到 subtitle——P1 实测踩坑）
- **拆行宽度铁律：每行宽度 ≤ 版心 80%（≈8.5in / 约 17 个中文字当量）**。满宽行（>9.5in）视觉上呈"左对齐块"破坏居中观感，且触发 LibreOffice 自动换行溢出叠 subtitle（P7 实测：含 15 中文字 + 12 拉丁的整行 ≈9.65in 失败；缩至 8.1in 后两行居中正常）。拉丁串按 ~0.55 字宽折算（12 拉丁 ≈ 6.6 中文字宽）
- `subtitle` 英文副题（灰 16pt）→ `claim` 主题句（酒红 18pt）→ `footer` 来源行（期刊/DOI/汇报日期，浅灰 11pt），均可选
- body 用 1 个 note 元素写**汇报用途**，文案模板（2026-08-10 定稿，面向正式汇报，勿加"面向导师/师兄"）：
  `{"type": "note", "term": "汇报用途", "explain": "文献阅读汇报 · 单篇精读"}`（综述 deck 用"综述精读"；多篇批次可在末尾附期刊名）
- **subtitle 禁止尾部拼接**：英文副题后不要挂"— 文献阅读汇报"之类（P5/P8 批量生成时混入过，封面会出现重复文案，视觉 QA 才抓到）
- 无 figure / table

### 论文信息页（point_figure + external 封面图）
- 内容四组 point：双语标题 / 文献信息（期刊·分区·IF·收录·卷期·DOI）/ 作者（通讯作者标注）/ 关键词
- **信息页排版容量规则（P7 实测，防文字溢出）**：point_figure 左栏 5.0in 文本框 ≈ **5 组 point 即饱和**（每组 lead/detail/so_what 3 行 + 段距 ≈ 0.9in；英文标题 detail 150 字符会换 3 行）→ 信息页 point **≤4 组**，或中英标题合并 + 精简
- **so_what 精简纪律**：与正文/其他 point 重复的 so_what 直接删（如英文标题点里的"期刊·年份"与文献信息点重复）；英文标题、关键词点可去 so_what；作者点 so_what 缩短为"通讯：XXX"
- **注入封面后必须复检 s02**：无图模式 → 注入 external 封面会从全宽正文切到左文右图，文字行数不变但栏宽变窄（12.1→7.3in），原本不溢出的内容可能溢出——改 JSON 后重渲 + 视觉复核信息页
- 右栏放**期刊封面图**：`figure.external: true`，`caption` 写"<期刊名> 期刊封面（装饰图）"；`bound_to` 可省略；**不写 `interpretation`**（装饰图无需"解读"行——渲染器已强制 external 图不渲染解读，数据侧也不填）
- 封面先用用户提供的本地图；如需检索，用现有浏览器或下载工具从出版商来源取得，不预设代理、端口、机器路径或额外服务。
- 下载后确认 Pillow 可打开且尺寸足够，再由主模型视觉确认是真实期刊封面而非占位图/logo，才放入当前版本的 `assets/figures/`。
- `source` 仍必填：`Source: 期刊封面, <期刊名>, <年份>`；取不到时说明缺失，不伪造封面。
- 分区/IF 可使用单独安装的 onescholar（非本插件依赖）或官方来源核验；无结果时省略或标为未核验，不填示例数值。

### 目录页（toc layout）
- body 每行一个 point：`lead` = "`NN · 章节名`"（20pt bold 大行）、`detail` = 一句副注（14pt 灰），垂直均匀分布
- 行数 ≤ 8（章节多时合并层级，不要堆小字）

### external 图纪律（数据纪律不放松）
- `external` 只豁免：source 图号正则、bound_to 必填、孤儿图检查（verify_plan 与 render2pptx 两处都豁免）
- **仍强制**：source 非空；禁止被正文 `fig_ref` 引用（装饰图不能当证据）；下载失败不静默丢弃
- 期刊封面等装饰图不要改造成证据图（无图注/无坐标可读，违反图证绑定）

### 重编号经验（正文前插 3 页）
- 原正文页 sN → s(N+3)：**用一次性脚本**同步改 `slide_id` 与所有 `bound_to` 前缀，禁止手改（漏一处 verify_plan 会报错）
- P1 实测 bound_to 全部自引用本页（`s10_发现2` 前缀即本页）→ 按"前缀机械替换"即可；若存在**跨页** bound_to（引用别的 slide_id），必须先建 `id_map` 全局映射再替换，且注意新旧 id 冲突（如 s04 旧页 vs s04 新封面）——先收集再统一替换，勿逐页就地改

### 附加页视觉 QA 重点
- 封面：标题是否溢出/叠行、整体居中
- 信息页：右栏封面图是否变形/占位、文字列宽
- 目录：行距均匀、lead/detail 无截断
- 新增 3 页与正文页一起全量渲染检查，不进"抽查"

## 批量多 deck 生产

多篇论文各生成独立 deck 时的规模化流程（每篇一个 deck，与单篇同构）。

### 元数据准备（阶段 0，主会话统一做）
- **元数据权威源 = MANIFEST 登记的当前 HTML 版本 page-header**（`_tmp/P<n>/html/versions/<html-version>/P<n>_<short-name>_<year>.html` 的 `.cite`/`.journal-info`/`.meta`/`.keywords` 行含期刊/分区 badge/IF/DOI/卷期/作者/关键词全套）——`_tmp/P<n>/raw/linked_fixed.md`（MANIFEST 登记时优先，否则 `linked.md`）只作输入兜底
- 缺的期刊指标或 DOI 用已有工具查证；不可用时标注缺失，不要求新增依赖
- 将每篇已核验元数据交给执行者；helper 复用这些证据，不自行补造元数据

### 封面批量获取与回填顺序（防漏步骤）
1. 获取封面（见「论文信息页」小节）→ Pillow + **视觉核验内容**
2. 先将实际封面路径传入当前论文的生成输入，再注入页面
3. 注入：把封面拷到 MANIFEST-resolved deck version 的 `assets/figures/journal_cover.png`，s02 加 `figure.external: true` 对象
4. **注入后必须重渲 + 双 verify + 视觉复检 s02**（无图→左文右图切换可能引发溢出，见信息页容量规则）

### 可选同模型 helper
- 默认由主模型完成。可选 helper 必须继承主模型，每个任务限定论文/页面、输入证据、插件相对工具路径、输出版本目录和验收标准；不嵌套派发
- **研究型任务先冻结 `slide_contract.json`**：同模型 helper 只负责按 contract 填充 `slide_plan.json`，不得自行改变页序、合并/拆分页面或新增科学结论；主会话独立复核 contract 一致性
- 并发数量遵循当前运行环境限制，避免多个执行者修改同一版本目录
- agent 验收：`verify_contract.py`（如有 contract）+ `verify_plan.py` + `verify_pptx.py` **exit 0** + 主模型语义 QA 全检 + 迭代修复

### 主会话终检（不信 agent 自报，独立复核）
- 全部 deck 独立复跑双 verify（exit 0 才算过）
- 主模型复核封面居中、信息页容量、目录行距等关键页面；不能仅依赖 helper 自报通过
- 汇总清单 `ppt_batch_summary.md`（每篇：deck/页数/封面/verify/QA/修复记录）

## Runtime and plugin paths

Commands run from this skill's directory, `skills/md2pptnote/`. Locate Python
and the user's prepared runtime; do not assume packages or executables are installed.
Rendering needs python-pptx and Pillow. Formula rendering additionally uses local
`xelatex`, `pdfcrop`, and `pdftoppm` discovered on PATH. Visual export can use
an available LibreOffice `soffice` plus `pdftoppm`; report missing tools as an
unverified visual step. Quote paths containing spaces.

Images come first from the registered paper's `raw/images/` and are copied to
the current deck version's `assets/figures/`, retaining hash filenames. The
sibling [pdf2md](../pdf2md/SKILL.md) provides native contact-sheet/mapping checks;
[md2htmlnote](../md2htmlnote/SKILL.md) provides the registered HTML header.
For a new project use [the synthetic example](../../examples/registered-paper/README.md).

All artifacts go to the user's selected project/output or archive target.
This skill supplies no standing authorization to commit, push, or publish.

`slides/save_version.py` remains a legacy local snapshot helper: it copies three
files to `<deck_dir>/versions/<label>/` and does not register MANIFEST versions
or update `current.json`. Do not use it to allocate new pipeline versions.
For new candidate/reviewed milestones use the existing MANIFEST/version contract.

## 统一路径规范（项目级，强制）

机器可读路径真相源是用户项目的 `_tmp/MANIFEST.json`；项目已有布局规范时同时遵循。
本 skill 遵循其登记与版本契约：

- 输入唯一是 MANIFEST 登记的 linked 源（`linked_fixed_md` 优先、回退 `linked_md`）；共享 `raw/` 同时包含 `full.md`、`images/`、`fig_health.md`（及可选修正版）
- 每个 deck 版本写入 `_tmp/P<n>/deck/versions/<deck-version>/`，并包含 `slide_contract.json`、`slide_plan.json`、`final_presentation_cn.pptx`、`qa_report.md`、`asset_manifest.md`、`assets/figures/`、`pages/`
- `_tmp/P<n>/deck/current.json` 的 `current_version` 只能是该论文 `deck.versions[]` 中已登记版本 ID 或 `null`；不得为空字符串、缺省或跨到 HTML 版本空间
- deck 版本 ID 与 HTML 版本 ID 独立，不要求相同；HTML page-header 只能从 MANIFEST 登记的当前 HTML 版本读取
- 新 candidate/reviewed milestone 使用新 deck version；同一版本内允许迭代覆盖
- 旧 `_tmp/<NN>-<简称>/` 根层 deck 与 `P<n>/P<n>_*.html` 根层 HTML 仅作 legacy/migration references，不是新产物规则
- 项目提供 `_tmp/scripts/pipeline_layout.py` / `check_image_refs.py` 时运行现有门控；它们不随插件提供。无这些工具时仍核对登记路径和图片引用，不另建注册框架。
