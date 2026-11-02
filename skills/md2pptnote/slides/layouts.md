# 预设 Layout 库

## 选用准则
- 图为主要证据且复杂 → `claim_figure`（图主导）或 `full_figure`
- 文本为主要论点，图作佐证 → `point_figure`（文本占宽 60-70%，图窄）
- 核心是问答式推理 → `question_answer`
- 数据对比为主 → `full_table`
- **MinerU 拆分的多面板图（Figure 7a–e 等多子图）→ `multi_figure`**
- **不默认 50/50 对称分栏**。图/文本谁重要谁占大
- 一页塞不下 → 拆分，不要压缩

## 8 种 layout

### 1. point_figure（非对称左文右图）
- 布局：section tag + title（顶部）| 左 60-70% body 论证链 | 右 30-40% 图
- body 渲染：point 元素 → lead 深色加粗 / detail 灰 / so_what 酒红；note → 灰色小字缩进

### 2. claim_figure（图主导 + 窄解读带）
- 布局：title（顶部）| 图占页 60%+ | 右侧窄带：claim + 2-3 条证据
- 适合：一张图能说明核心结论的页

### 3. question_answer
- 布局：title（顶部）| 大字号 question | answer 分段 | 底部 takeaway 酒红条
- 适合：问答推进型内容（如"为什么对称炉腔却温度不均"）
- 约束：仅支持 **1 个** `qa` 元素（多个 qa 会被拒绝并报错；body 可带少量 note 等辅助元素，排在 qa 之后）

### 4. full_table
- 布局：title（顶部）| 全宽表格 | 表下强调文字（酒红）
- **图文模式**：带 `figure` 时 → 正文论证链紧凑排表上方 + 表格左 60% + 图右栏窄 40%（对齐 point_figure 分栏）。适合"数据对比表 + 一张支撑图"的页（如 s06 配 P8 Fig 11 温度曲线，直接可视化表格里的 155°C/TAL 数据）
- 适合：热源对比 / 场景矩阵 / 可靠性数据表；表+图共存时用图文模式

### 5. full_figure
- 布局：title（顶部）| 全宽图 | 图下 caption + interpretation + source
- 适合：核心证据图单独成页

### 6. multi_figure（多面板图栅格）
- 布局：title（顶部）| 栅格区（面板 ≤2 单列、3–6 双列、≥7 三列；末行单面板整行居中；单元格内图片等比铺满、不裁切）| 底部统一图注
- 子图角标：每张子图左上角 `(a)`/`(b)`…（无 label 时自动按顺序生成）
- 图注：caption + subcaptions + interpretation + source 统一放底部
- 适合：MinerU 把一个完整图拆成多个 CDN 链接的多面板图
- **精选原则**：不必全放所有子图——只放与页内结论相关、需重点解释的面板（2-3 张往往比 6-7 张更清晰）。无关/低信息面板剔除，speaker notes 提一句
- 约束：`figure.panels` 必填且非空（≤9 个子图）；每项 `path` 必填
- **方向词规范**：正文/figread/speaker_note 引用面板时，方向词必须按实际排列写——≤2 面板单列 = **上/下图**（"上图为…下图为…"），3-6 双列 = 左/右/左上/右下等。禁止"左图/右图"描述单列布局（P10 s04 实测踩坑：2 面板单列却写"左图右图"）

### 7. cover（封面）
- 布局：居中大标题（34pt，可含 `\n` 手动换行）+ 英文副题（灰）+ 主题句 claim（酒红）+ body 居中列 + 底部 `footer` 来源行（期刊/DOI/日期）
- 适合：deck 第一页。`subtitle` / `claim` / `footer` 均可选；**中文标题 >20 字必须手动拆两行**（渲染器不自动换行，超长会溢出叠到 subtitle——P1 实测踩坑）
- 无 figure / table

### 8. toc（目录）
- 布局：title（顶部）+ body 的 point 元素渲染为编号章节大行（lead 20pt bold + detail 灰注），垂直均匀分布
- 适合：正文前目录页；每行一个 point（lead=`NN · 章节名`，detail=一句副注），行数 ≤8
- 无 figure / table

## 每页信息密度上限
- body 元素 ≤ 5 个
- 每元素 text 长度：lead/question ≤ 30 字，detail/answer ≤ 40 字，so_what/takeaway ≤ 30 字
- 超限 → 精简或拆分
