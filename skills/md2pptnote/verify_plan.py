#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""slide_plan.json 图注一致性校验（提炼阶段护栏，渲染前跑）。

在提炼 slide_plan.json 后、渲染前执行，拦下"图注对不上/图号模糊"这类语义错误——
这类错误渲染器结构校验抓不到（图能放进去），但视觉验收才发现的成本很高。

检查项：
1. figure.source 必须是精确图号格式 `Fig. N` 或 `Fig. N[面板]`（正则），
   禁止"Fig. 吸收率数据"这类模糊描述；必须含 [P#] 文献标号
2. figure.bound_to 必须指向页内真实存在的结论 id（point.lead / qa.question /
   ced.claim 的锚点，或 slide.claim）
3. figure.path / panels[].path 引用的图片文件必须存在
4. 输出"图注清单"：每页图 + source + caption + bound_to，供自查

用法: python verify_plan.py slide_plan.json
退出码 0=通过，1=有违规。
"""
import json
import re
import sys
from pathlib import Path

# figure.source 精确格式：
#   "Source: Fig. N" / "Fig. N[面板]" / "Fig. N (a–c)" + 文献标号。
# 文献标号两种合法形式：`[P#]`（综述内引用）或期刊年份（如 ", *Materials*, 2024"）。
# 但必须以精确图号开头——"Fig. 吸收率数据"这类模糊描述不匹配，被拦下。
_SOURCE_RE = re.compile(
    # 图号允许附录形式（`Fig. A.1` / `Fig. S2`）——字母小节号 + 序号
    r'^Source:\s*Fig(?:ure)?\.?\s*(?:[A-Za-z]\.\s*)?\d+[a-z]?\s*(?:\([^)]*\))?\s*,'
    r'\s*(?:\[P\d+\]|[一-鿿A-Za-z&*()·,.\s]*\d{4})$',
    re.IGNORECASE,
)
# 归一化前先剥掉 "Source:" 与 "Fig./Figure" 前缀，避免 "Fig. 1" 里的
# "g. 1" 被误判成附录编号；剥不掉（fig_ref 只写 "A.1"）就直接解析。
_FIG_PREFIX_RE = re.compile(r'^\s*(?:Source:\s*)?(?:Fig(?:ure)?\.?\s*)?', re.IGNORECASE)


def _collect_conclusion_anchors(slide: dict) -> set[str]:
    """页内所有可被 bound_to 指向的结论锚点。"""
    anchors = set()
    for el in slide.get("body", []):
        if not isinstance(el, dict):
            continue
        t = el.get("type")
        if t == "point" and el.get("lead"):
            anchors.add(el["lead"])
        elif t == "qa" and el.get("question"):
            anchors.add(el["question"])
        elif t == "ced" and el.get("claim"):
            anchors.add(el["claim"])
    if slide.get("claim"):
        anchors.add(slide["claim"])
    return anchors


def _norm_fig(text: str) -> str:
    """从 'Fig. 6h' / 'Fig. 6 (a–c)' / 'Fig. A.1' / '图6' 提取规范化图号。

    正文图号取数字（'6'）；附录图号取「字母+序号」（'A.1' → 'a1'），避免与正文
    'Fig. 1' 混同。提取不到返回原串（让其与任何规范化图号不等）。
    """
    stripped = _FIG_PREFIX_RE.sub("", str(text), count=1)
    m = re.match(r"([A-Za-z])\.\s*(\d+)", stripped)
    if m:
        return f"{m.group(1).lower()}{m.group(2)}"
    m = re.search(r'(\d+)', stripped)
    return m.group(1) if m else str(text)


def _ref_figs(slide: dict) -> list[str]:
    """页内所有正文元素声明的 fig_ref。"""
    refs = []
    for el in slide.get("body", []):
        if isinstance(el, dict) and el.get("fig_ref"):
            refs.append(el["fig_ref"])
    return refs


def _has_figread(slide: dict) -> bool:
    """页内是否有 figread 读图元素。"""
    return any(isinstance(el, dict) and el.get("type") == "figread"
               for el in slide.get("body", []))


def verify_plan(plan: dict, base_dir: Path) -> tuple[list[str], list[str]]:
    """返回 (违规列表, 提醒列表)；违规非空 = 不通过，提醒仅提示不阻断。"""
    errors: list[str] = []
    notes: list[str] = []
    for s in plan.get("slides", []):
        sid = s.get("slide_id", "?")
        fig = s.get("figure")
        refs = _ref_figs(s)

        # figread.axes 残留检查：axes 只描述真实坐标轴（横轴/纵轴/数值轴/曲线），
        # 出现"无坐标轴"类标记 = 非坐标轴图仍填了 axes（生成侧漏清理）→ 违规
        for el in s.get("body", []):
            if isinstance(el, dict) and el.get("type") == "figread" and el.get("axes"):
                if re.search(r"无坐标轴|无定量坐标轴|无数值坐标轴", el["axes"]):
                    errors.append(
                        f"[{sid}] figread.axes 含'无坐标轴'类标记: '{el['axes'][:40]}…' —— "
                        f"非坐标轴图请删除 axes 字段（内容介绍放 shows）"
                    )
        if not fig:
            # 3b. 正文引用了图（fig_ref）但本页没有 figure → 违规
            # 软提醒只在没有 fig_ref 违规时给出，避免冗余噪音
            if _has_figread(s) and not refs:
                notes.append(f"[{sid}] 有 figread 但本页无 figure（读图内容应紧跟图）")
            if refs:
                errors.append(f"[{sid}] 正文元素有 fig_ref={refs} 但本页没有 figure")
            continue

        # 软提醒：有图但没配 figread 读图内容（装饰性示意图可豁免）
        if not _has_figread(s):
            notes.append(f"[{sid}] 有图但无 figread 读图内容，检查是否漏配（装饰性示意图可豁免）")

        # 装饰性外部图（如期刊封面）：不承担图证绑定职责——
        # 跳过 source 图号正则 / bound_to / 孤儿图检查（正文不必引用装饰图），
        # 但 source 仍必须非空（来源标注），且不允许当作证据图（fig_ref 引用它同样报错）。
        if fig.get("external"):
            if not fig.get("source"):
                errors.append(f"[{sid}] figure.external 仍需 source（装饰图也要标注来源）")
            for ref in refs:
                errors.append(f"[{sid}] figure.external 是装饰图，正文元素不能 fig_ref 引用它: {ref}")
            continue

        # 1. source 精确格式
        src = fig.get("source", "")
        if not src:
            errors.append(f"[{sid}] figure 缺 source")
        elif not _SOURCE_RE.match(src):
            errors.append(
                f"[{sid}] source 格式不规范: '{src}' —— 应为 'Source: Fig. N[面板], [P#]'"
            )

        # 2. bound_to 指向页内结论。两种合法形式：
        #    a) 以 {slide_id}_ 开头（语义锚点，如 s05_ced / s01_point2）——指向本页
        #    b) 精确命中页内某条结论的文本锚点
        bound = fig.get("bound_to", "")
        anchors = _collect_conclusion_anchors(s)
        if not bound:
            errors.append(f"[{sid}] figure 缺 bound_to（图必须证明页内某结论）")
        elif not (bound.startswith(f"{sid}_") or bound in anchors):
            errors.append(
                f"[{sid}] bound_to='{bound}' 既不是本页锚点({sid}_*)也不在结论文本里"
            )

        # 3a. 图证绑定双向：图必须被至少一个正文元素 fig_ref 引用（不能是孤儿图）
        if not refs:
            errors.append(
                f"[{sid}] 图未被任何正文元素 fig_ref 引用（正文结论前要写'如图 N 所示'）"
            )
        else:
            # 3c. 图号一致性：所有 fig_ref 的主图号必须与 source 主图号一致（防漂移）
            src_num = _norm_fig(src)
            for ref in refs:
                if _norm_fig(ref) != src_num:
                    errors.append(
                        f"[{sid}] 正文引用 fig_ref='{ref}' 与 source 图号 '{src}' 不一致"
                    )

        # 4. 图片文件存在
        paths = []
        if fig.get("panels"):
            paths.extend(p.get("path", "") for p in fig["panels"])
        elif fig.get("path"):
            paths.append(fig["path"])
        for p in paths:
            if not p:
                continue
            # 支持 assets/figures/... 相对 base_dir；也支持绝对/相对文件
            cand = base_dir / p
            if not cand.exists():
                errors.append(f"[{sid}] 图片不存在: {p}")

    return errors, notes


def print_manifest(plan: dict) -> None:
    """输出图注清单（每页图 + source + caption + bound_to），供 agent 自查。"""
    print("== 图注清单 ==")
    for s in plan.get("slides", []):
        fig = s.get("figure")
        if not fig:
            continue
        sid = s["slide_id"]
        n = len(fig.get("panels", [])) if fig.get("panels") else 1
        kind = f"{n}面板" if fig.get("panels") else "单图"
        print(f"[{sid}] {kind} | source={fig.get('source','')} | bound_to={fig.get('bound_to','')}")
        print(f"      caption: {fig.get('caption','')[:60]}")
        if fig.get("subcaptions"):
            print(f"      sub: {fig['subcaptions'][:70]}")


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python verify_plan.py slide_plan.json")
        sys.exit(1)
    plan_path = Path(sys.argv[1])
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    base_dir = plan_path.parent
    errors, notes = verify_plan(plan, base_dir)
    print_manifest(plan)
    if notes:
        print("\n== 提醒（warning，不阻断）==")
        for n in notes:
            print(f"  ○ {n}")
    if errors:
        print("\n== 违规项 ==")
        for e in errors:
            print(f"  ✗ {e}")
        print(f"\n{len(errors)} 项违规")
        sys.exit(1)
    print("\n图注一致性校验通过 ✓")


if __name__ == "__main__":
    main()
