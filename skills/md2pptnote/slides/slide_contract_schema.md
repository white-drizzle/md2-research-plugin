# slide_contract.json Schema

`slide_contract.json` 是研究型 PPT 的叙事规划层，位于原文理解和 `slide_plan.json` 渲染计划之间。

## 目的

- `slide_contract.json` 回答“为什么这样讲”。
- `slide_plan.json` 回答“如何渲染”。
- contract 由主模型制定，子模型只能按 contract 执行，不得自行改变页序或科学结论。

## 顶层结构

```jsonc
{
  "meta": {
    "purpose": "research presentation narrative plan",
    "source": "_tmp/P11/raw/linked.md",
    "central_message": "全文最终希望听众记住的一句话",
    "facts_policy": "原文事实优先；推断必须显式标注"
  },
  "workflow": ["问题", "建模", "优化", "结果"],
  "slides": [ /* 每页一个 contract 对象 */ ],
  "global_guardrails": ["全局科学边界"]
}
```

## slide contract 对象

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `slide_id` | string | ✅ | 与 `slide_plan.json` 完全一致，如 `s07` |
| `section` | string | ✅ | 短的一行章节标签，如 `02 · 温度场与 PCB 响应` |
| `one_sentence_message` | string | ✅ | 本页唯一主旨，读者看完应能复述 |
| `audience_question` | string | ✅ | 本页回答的听众问题 |
| `must_show` | string[] | ✅ | 本页必须出现的内容 |
| `must_not_show` | string[] | ✅ | 本页禁止出现的内容/表达 |
| `evidence` | string[] | ✅ | 原文文件和行号、表号、图号或数据来源 |
| `input` | string | 否 | 本页输入 |
| `process` | string | 否 | 本页模型/方法处理 |
| `output` | string | 否 | 本页输出 |
| `bridge_from_previous` | string | 推荐 | 上一页如何导向本页 |
| `bridge_to_next` | string | 推荐 | 本页如何导向下一页 |
| `scientific_caveat` | string[] | 否 | 论文缺口、反推变量、适用边界 |

## 设计规则

1. 每页只能有一个 `one_sentence_message`。
2. `must_show` 决定页面保留什么，`must_not_show` 防止子模型回填无关内容。
3. 复杂模型页优先写清 `input → process → output`：环境输入、模型响应、优化输出不能混为一谈。
4. 公式必须写明角色：起点、化简过程、最终计算公式或评价指标。
5. 优化论文必须区分：决策变量、目标函数、约束、候选解集、最终选点。
6. “最优、显著、接近、工程可用”等结论必须能在 `evidence` 中找到支持。
7. `section` 默认保持一行短标签；不要把整句解释塞进页眉。

## 与 slide_plan 的一致性

运行：

```bash
python verify_contract.py slide_contract.json slide_plan.json
```

验证器检查：

- contract 页数和 `slide_id` 连续且唯一；
- contract 与 slide_plan 页序一致；
- 两者 `section` 一致；
- 必填规划字段存在且为非空字符串/数组。

验证器**不使用脆弱的正则表达式判断文案质量**。语义质量由主模型的盲读 QA 完成。
