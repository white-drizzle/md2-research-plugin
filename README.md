# MD2 Research

一个插件，三个技能入口：

| 技能 | 用途 |
| --- | --- |
| `md2-research:pdf2md` | PDF → Markdown、图片和拆图核验 |
| `md2-research:md2htmlnote` | 中文解读或逐段双语阅读 HTML |
| `md2-research:md2pptnote` | 有证据绑定的中文学术汇报 PPTX |

HTML 的双语模式保留原文公式编号、语义颜色和原文/译文开关。原生多模态模型直接核验图片与渲染结果。期刊指标查询可使用已安装的 `onescholar`，它独立于本插件。

## 安装

从本地克隆目录注册并安装：

```text
codex plugin marketplace add /path/to/md2-research-plugin
codex plugin add md2-research@md2-research
```

也可在有仓库访问权限的环境中直接添加 GitHub 来源：

```text
codex plugin marketplace add white-drizzle/md2-research-plugin
codex plugin add md2-research@md2-research
```

本仓库公开分发。无需 MCP 服务或 CC Switch 配置。

## 使用

在 Codex 中选择 MD2 Research，或指定技能与来源文件：

- “使用 md2htmlnote，生成中文导师汇报笔记。”
- “使用 md2htmlnote，生成逐段中英对照，保留原文公式编号并添加语义标注。”
- “使用 md2pptnote，根据论文生成学术汇报。”

三个技能的说明与工具都在 `skills/` 中，公共文件通过插件内相对路径复用。

## 运行环境与检查

Python 3.12+。HTML 校验器只需标准库；拆图接触表和 PPT 工具需要现有依赖：

```text
python -m pip install -r requirements.txt
python scripts/test_skills.py
```

只有通过 SDK 实际解析 PDF 时才需要：

```text
python -m pip install -r requirements-pdf.txt
```

MinerU 凭据通过 `MINERU_TOKEN` 或已有配置提供，不随插件分发。PPT 公式及其测试需要 PATH 中的 `xelatex`、`pdfcrop`、`pdftoppm`。PDF/页面截图验收需要本机浏览器或文档渲染器。

HTML 图片可内嵌离线使用；原模板仍从 CDN 加载 MathJax。双语原模板在手机目录关闭操作上有已知遮挡限制，合并时保持模板内容不变。

## 来源与迁移

此仓库整合了此前独立维护的 pdf2md、md2htmlnote 和 md2pptnote。保留三个技能边界；md2htmlnote 已包含双语模式，视觉检查在各技能内执行。已有源码与授权声明按来源保留，本次迁移不新增公开授权范围。

插件格式参考 [OpenAI 官方文档](https://developers.openai.com/plugins/build/plugins)。

