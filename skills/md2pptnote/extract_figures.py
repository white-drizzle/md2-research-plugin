#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MinerU MD 图组提取器（提炼阶段半自动工具）。

输入任意 MinerU 导出的 .md，输出每个 Figure 图组的图片链接清单 + 图注 + 子图标签，
帮助 agent 在提炼 slide_plan.json 时正确选图、填 panels、写 source。

## 核心归属规则（防漏图错位）
**图片链接归属 = 它后面最近的下一个 Figure caption 的编号**，绝不按"图片组顺序序号"对应编号。
MinerU 可能漏图（某个 figure 的图片缺失），但 caption 一般保留。若遇到"caption 前无图链接"，
标记 [疑似漏图]，但该空缺绝不导致后续链接错位——后续链接仍归属下一个 caption。

算法：pending 暂存图片 → 遇到下一个 caption 时，把暂存图片全部归属给它 → 清空暂存。
"""
import re
import sys
from pathlib import Path

# Figure caption 识别：行首 "Figure N." 或 "Fig N."，编号后紧跟点号，独立成行。
# 排除正文引用（"Figure 11 illustrates..." 编号后是动词、"as shown in Fig. 2" 嵌长句）。
_CAPTION_RE = re.compile(
    r'^(?:Figure|FIG\.?|Fig\.?|图)\s*(\d+)\.\s',
    re.IGNORECASE,
)
# 图片链接行（兼容 MinerU 两种导出：`![image](url)` 旧版 / `![](url)` 空 alt 新版）
_IMG_RE = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
# 独立的子图标签行，如 "(a)" "(b)" 或 "a)" "b"（多面板图到 j/k 也有，放宽到 a-z）
_LABEL_RE = re.compile(r'^\s*\(?([a-zA-Z])\)?\s*$')


def _is_caption(line: str) -> bool:
    """判断一行是否为真实 Figure caption（vs 正文里的 Figure 引用）。"""
    m = _CAPTION_RE.match(line.strip())
    if not m:
        return False
    # 独立成行（不含正文长句特征）：caption 通常是一行的完整句
    return True


def extract_figures(text: str, warn_missing: bool = True) -> list[dict]:
    """从 MinerU MD 文本提取图组。

    返回按出现顺序排列的图组列表，每项：
      {number, caption, urls: [url,...], labels: {url: label}, line, missing_img}
    归属规则见模块 docstring。
    """
    lines = text.splitlines()
    groups: list[dict] = []
    pending_urls: list[tuple[int, str]] = []   # (行号, url) 暂存

    for i, ln in enumerate(lines):
        im = _IMG_RE.search(ln)
        cap = _is_caption(ln)
        if im:
            pending_urls.append((i, im.group(1)))
            continue
        if cap:
            m = _CAPTION_RE.match(ln.strip())
            number = int(m.group(1))
            caption = ln.strip()
            groups.append({
                "number": number,
                "caption": caption,
                "urls": pending_urls,
                "labels": {},
                "line": i,
                "missing_img": len(pending_urls) == 0,
            })
            pending_urls = []

    # 尾部未闭合的图片（无后续 caption）单独列出
    if pending_urls:
        groups.append({
            "number": None,
            "caption": "(文件末尾未闭合图组)",
            "urls": pending_urls,
            "labels": {},
            "line": None,
            "missing_img": False,
        })

    # 收集子图标签：图片上方 2–4 行内的独立 "(a)" 标签（MinerU 实际：标签行 + 空行 + 图片）。
    # 从图片最近处向上找，取最近标签；第一张图 / 无标签图不设标签（a 常隐含在图注里）。
    for g in groups:
        for ln_no, url in g["urls"]:
            label = None
            for d in range(-1, -5, -1):
                i = ln_no + d
                if 0 <= i < len(lines):
                    lm = _LABEL_RE.match(lines[i].strip())
                    if lm:
                        label = f"({lm.group(1)})"
                        break
            if label:
                g["labels"][url] = label

    if warn_missing:
        for g in groups:
            if g["missing_img"] and g["number"] is not None:
                print(f"[警告] Figure {g['number']} (L{g['line']}) 前无图片链接，疑似 MinerU 漏图"
                      f"——后续链接仍按下一 caption 归属，不因空缺错位。")
    return groups


def _fmt_url(u: str) -> str:
    return u[-30:]


def report(md_path: Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    groups = extract_figures(text)
    print(f"== {md_path.name} : {len([g for g in groups if g['number']])} 个图组 ==")
    for g in groups:
        if g["number"] is None:
            continue
        n = len(g["urls"])
        flag = "  [疑似漏图]" if g["missing_img"] else ""
        print(f"\nFigure {g['number']}  (L{g['line']})  {n} 张图{flag}")
        print(f"  图注: {g['caption'][:80]}")
        for ln_no, u in g["urls"]:
            lab = g["labels"].get(u, "")
            print(f"    L{ln_no} {lab:5} {_fmt_url(u)}")


def to_json(groups: list[dict]) -> list[dict]:
    """图组清单的 JSON 可序列化形式（urls/labels 从 tuple/键值对转 list/dict[str]）。"""
    return [{
        "number": g["number"],
        "caption": g["caption"],
        "line": g["line"],
        "missing_img": g["missing_img"],
        # urls: [(行号, url)] -> [{"line": …, "url": …, "label": …}]
        "images": [{"line": ln, "url": u, "label": g["labels"].get(u)} for ln, u in g["urls"]],
    } for g in groups]


def main() -> None:
    import json
    import argparse
    ap = argparse.ArgumentParser(description="MinerU MD 图组提取器")
    ap.add_argument("md_files", nargs="+", help="一个或多个 MinerU .md 文件")
    ap.add_argument("--json", metavar="OUT.json", default=None,
                    help="同时把图组清单写成 JSON（机器可读，供提炼阶段作为输入）")
    args = ap.parse_args()
    for p in args.md_files:
        report(Path(p))
    if args.json:
        all_groups: list[dict] = []
        for p in args.md_files:
            text = Path(p).read_text(encoding="utf-8")
            groups = extract_figures(text, warn_missing=False)
            all_groups.append({"paper": Path(p).name, "groups": to_json(groups)})
        out = Path(args.json)
        out.write_text(json.dumps(all_groups, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"图组 JSON 已写入: {out}")


if __name__ == "__main__":
    main()
