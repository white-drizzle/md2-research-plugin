# slide_plan.json Schema

顶层结构：
```jsonc
{
  "meta": { "title": "…", "subtitle": "…", "date": "…", "source_papers": "…" },
  "slides": [ /* 每页一个 slide 对象 */ ]
}
```

## slide 对象

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `slide_id` | string | ✅ | 如 `s10` |
| `title` | string | ✅ | 结论式标题（如"ADRC 把误差从 20°C 压到 4°C"） |
| `section` | string | 否 | 单行短章节标签（建议不超过 32 字符，如"02 · 温度场与 PCB 响应"） |
| `claim` | string | 否 | 页级一句话结论。`claim_figure` 布局会渲染；`point_figure` 布局的结论由 `point.lead` 承载；其他布局可选 |
| `subtitle` | string | 否 | 标题下灰色小字 |
| `body` | array | ✅ | 论证链（顺序即逻辑），元素类型见下 |
| `figure` | object | 否 | 见 figure 对象 |
| `table` | object | 否 | 见 table 对象 |
| `speaker_note` | string | ✅ | 一句话备注（正式汇报不写演讲稿） |
| `layout` | string | ✅ | 从 layouts.md 预设中选 |

## body 元素类型

### point（结论前置三段式）
```jsonc
{ "type": "point", "lead": "结论", "detail": "证据/数据", "so_what": "启示",
  "fig_ref": "6h" }   // 可选：本结论由本页哪张图支撑（渲染结论句前缀"如图 6h 所示，"）
```

### qa（问答叙事式）
```jsonc
{ "type": "qa", "question": "问题", "answer": "答案", "takeaway": "一句话收获",
  "fig_ref": "6" }   // 可选
```

### note（名词解释）
```jsonc
{ "type": "note", "term": "名词", "explain": "一句人话解释" }
```

### ced（页级 Claim-Evidence-Data）
```jsonc
{
  "type": "ced", "claim": "结论",
  "evidence": ["证据1", "证据2"],
  "data": "关键数据（高亮）",
  "fig_ref": "10 (a–c)"   // 可选：claim 由本页哪张图支撑
}
```

### figread（读图指引，紧跟在"如图 N 所示"结论元素之后）
```jsonc
{
  "type": "figread",
  "axes": "坐标轴含义（横轴/纵轴单位与范围）",
  "legend": "图例含义（颜色/线型/符号代表什么）",
  "shows": "图意（这张图表明了什么，通常引关键数值）"
}
```
- 渲染为灰色小字：`坐标轴：`/`图例：`/`图意：` 三行（有值才渲染），紧跟结论元素，让听众不看原文也能读懂图；**无"读图"小标题**（该词 AI 感强，正式汇报不出现，2026-08-10 定稿）
- 图读法要求：讲清"图里坐标是什么、颜色/符号代表什么、图想说明什么结论"
- **axes 只填真坐标轴图**（曲线/散点/柱状/3D 曲面/热像带数值轴）：写横/纵轴变量与范围。示意图/照片/SEM/显微/云图/等值线/框图/工艺流程等**省略 axes 字段**，图片内容介绍放 `shows`；axes 含"无坐标轴"类字样 = 残留标记（verify_plan 报错），清理时标尺/色标/单位等有价值片段迁入 `shows` 或 `legend`
- 数值必须来自 MD 原文，配图前先经视觉核验图的实际类型（热力图 vs 分布曲线 vs 照片）

**`fig_ref`（图证双向绑定）**：`point.lead` / `qa.question` / `ced.claim` 可加 `fig_ref` 声明"这句结论靠本页哪张图支撑"。渲染时结论句前加酒红前缀"如图 xx 所示，"（与图注 source 同色，形成视觉锚点）。**选图与正文的衔接必须在正文里写出来**，不是只存 JSON。规则：
- 主图号（`fig_ref` 里第一个数字）必须与 `figure.source` 图号一致（verify_plan 强制，防图号漂移）
- 每页图必须被至少一个正文元素引用（孤儿图违规）；正文引用但本页无图也违规
- 值用精确图号（`6h` / `10 (a–c)`），与 `source` 同规格

## figure 对象

| 字段 | 必填 | 说明 |
|---|---|---|
| `path` | 见注 | 图片相对路径（相对 output/）。**无 `panels` 时必填**（单图）；有 `panels` 时可省略 |
| `panels` | 否 | 多面板图子图数组（MinerU 拆分的子图），见下。**`multi_figure` 布局必填** |
| `caption` | ✅ | 中文图注（整图统一图注） |
| `bound_to` | ✅ | 证明页内哪个结论（如 `s10_发现2` 或 `s11_claim`） |
| `interpretation` | ✅ | 解读：这张图为何在此、证明什么 |
| `source` | ✅ | `Source: Fig. X, [P#]` 或期刊年份；external 图也必须填写非空 source |
| `subcaptions` | 否 | 多面板子注：`(a)…; (b)…` 逐面板一句话描述（吸收自 MD 图注，不单独成段） |
| `external` | 否 | `true` = 装饰性外部图（如期刊封面），不承担图证绑定：跳过 source 图号正则 / bound_to / 孤儿图检查，但 source 仍必填、不允许被正文 `fig_ref` 当作证据引用。source 建议格式：`Source: 期刊封面, <期刊名>, <年份>`。**`interpretation` 不渲染**（渲染器对 external 图强制跳过"解读"行），数据侧也不填 |

### panels 数组（多面板图）

MinerU 会把一张多面板图（如 `Figure 7a–e`）拆成多个连续 CDN 图片链接 + 末尾统一图注。提炼时必须**收集全部子图**而非只挑一张。

```jsonc
{
  "path": "assets/figures/P9_shear-a.jpg",   // 单面板退化时用第一张（保持向后兼容）
  "panels": [
    { "path": "assets/figures/P9_shear-a.jpg", "label": "(a)" },
    { "path": "assets/figures/P9_shear-b.jpg", "label": "(b)" },
    { "path": "assets/figures/P9_shear-c.jpg", "label": "(c)" }
  ],
  "caption": "MET/HET 条件下 FHE 焊点剪切力对比",
  "subcaptions": "(a) 未受力; (b) 施加剪切力; (c) 剪断后界面",
  "bound_to": "s15_ced",
  "interpretation": "剪切力峰值直接反映焊点结合强度——MET 显著高于 LET/HET",
  "source": "Source: Fig. 6, [P9]"
}
```

**panels 规则：**
- 每项 `{ "path": 必填, "label": 可选 }`；`label` 缺省时按顺序自动生成 `(a)(b)(c)…`
- **不必全放**：只放与页内结论关联的子图，或需要重点解释的子图。信息量低、与本页结论无关的面板可剔除（放 speaker notes 提一句即可）。`subcaptions` 相应精简，只描述放上去的面板
- 数量上限 9（栅格 ≤3 列 × 3 行），超出请拆分到多页或精简
- `subcaptions` 把 MD 图注里的 `a–f)` 描述吸收为 `(a)…; (b)…`，不要渲染成独立段落
- 图片去重：同一 URL 出现多次只保留第一张（MinerU 偶发重复）
- **单面板退化**：`panels` 只有 1 项且 layout 不是 `multi_figure` 时，渲染器取该面板按单图渲染（顶层 `path` 可省略）；`multi_figure` 布局下 `panels` 必填且非空

## table 对象

`full_table` 正文页默认最多 10 行数据（不含表头）；超过请拆分或改用专门图表页，避免正式汇报中表格字号和行高不可读。

```jsonc
{
  "headers": ["指标", "NIR 卤素灯", "MIR 陶瓷"],
  "rows": [["加热速率", "20–22°C/s", "3–4°C/s"]],
  "col_widths": [2, 3, 3],
  "note": "表下方强调文字（可选）"
}
```

## 完整示例

### point_figure（左文右图，point 三段式 + note 名词解释）
```jsonc
{
  "slide_id": "s01",
  "title": "为什么关注红外焊接？",
  "claim": "红外焊接是柔性电子组装的优选热源，但面临光谱匹配与阴影效应两大挑战",
  "body": [
    { "type": "point", "lead": "能量定向、设备简单、升降温可控", "detail": "FPCB/BGA/FHE 对热应力敏感", "so_what": "适合柔性电子低温组装" },
    { "type": "note", "term": "FHE", "explain": "柔性混合电子：柔性基板上集成刚性和柔性元件" }
  ],
  "figure": {
    "path": "assets/figures/P9_trans.jpg",
    "caption": "材料透射光谱 vs NIR 光源能谱",
    "bound_to": "s01_claim",
    "interpretation": "PET 高透射、焊膏/银迹线高吸收——选择性加热的光学基础",
    "source": "Source: Fig. 2b, [P9]"
  },
  "speaker_note": "红外焊接用光子直接耦合加热，比热风介质升温快。",
  "layout": "point_figure"
}
```

### claim_figure（图主导，ced 元素承载 Claim-Evidence-Data）
```jsonc
{
  "slide_id": "s02",
  "title": "[P7] IPL 极速焊接：IMC 可控 + 跌落可靠性 2.68×",
  "claim": "极速加热使 IMC 厚度精确可控，直接转化为跌落可靠性收益",
  "body": [
    { "type": "ced", "claim": "IMC 厚度与跌落可靠性线性反比",
      "evidence": ["IPL 8–16s 焊接", "IMC 1.2–4.7 μm 可控"],
      "data": "y = -36.17x + 321.50, R²=0.973 · 跌落 2.68×" }
  ],
  "figure": {
    "path": "assets/figures/P7_drop.jpg",
    "caption": "跌落可靠性 vs IMC 厚度",
    "bound_to": "s02_ced",
    "interpretation": "跌落失效与 IMC 厚度线性反比——IMC 越薄可靠性越高",
    "source": "Source: Fig. 10, [P7]"
  },
  "speaker_note": "IPL 可精确控制 IMC，2.68 倍可靠性 + 40% 节能。",
  "layout": "claim_figure"
}
```

### question_answer（问答式，qa 元素 + 可选 note）
```jsonc
{
  "slide_id": "s03",
  "title": "[P4] 红外桌面回流炉：辐射主导低风速传热",
  "claim": "低 Re 时辐射主导传热",
  "body": [
    { "type": "qa", "question": "为什么对称炉腔却温度不均？",
      "answer": "离心风扇扰流破坏对称，后部偏热、对称面偏冷 1.2×",
      "takeaway": "板位选择要靠 CFD，不能靠炉子对称直觉" }
  ],
  "speaker_note": "P4 揭示辐射主导低风速传热。",
  "layout": "question_answer"
}
```

### multi_figure（多面板图栅格，panels 必填）
```jsonc
{
  "slide_id": "s15",
  "title": "[P9] 不同 NIR 条件焊点剪切力对比",
  "body": [
    { "type": "ced", "claim": "MET 焊点结合强度最优",
      "evidence": ["三种 NIR 设置 LET/MET/HET", "剪切测试国际标准"], 
      "data": "MET 剪切力 ~18 N · LET/HET <10 N" }
  ],
  "figure": {
    "panels": [
      { "path": "assets/figures/P9_shear-a.jpg", "label": "(a)" },
      { "path": "assets/figures/P9_shear-b.jpg", "label": "(b)" },
      { "path": "assets/figures/P9_shear-c.jpg", "label": "(c)" }
    ],
    "caption": "不同 NIR 设置下 SMD 焊点剪切前后照片",
    "subcaptions": "(a) 未受力; (b) 施加剪切力; (c) 剪断后界面",
    "bound_to": "s15_ced",
    "interpretation": "剪切力峰值直接反映焊点结合强度——MET 显著高于 LET/HET",
    "source": "Source: Fig. 6, [P9]"
  },
  "speaker_note": "P9 多面板图：MinerU 拆成 3 个子图，统一图注。",
  "layout": "multi_figure"
}
```
