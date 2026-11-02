# fig_health.py（拆图健康检查：图注解析 + 链接归属 + 比对报告）
# -*- coding: utf-8 -*-
r"""fig_health.py — 拆图健康检查：图注子图数 vs 图片链接数比对（MinerU 乱序/分割不全检出）。

用法: python fig_health.py <P<n>>/raw   （输出 <raw>/fig_health.md）
解析规则:
  - Figure caption: ^Figure (\d+)\. 行
  - 子图数: 范围写法 a–f / a-f / a–c、枚举 a) b) c)、d,e 枚举；跨段累加去重；无角标=1
  - 图片链接归属: full.md 中 ![](images/...) 归属其后最近的 Figure caption
"""
import re
import sys
from pathlib import Path

CAP_RE = re.compile(r"^(?:Figure|Fig)\.?\s+(\d+)\.", re.IGNORECASE)
IMG_RE = re.compile(r"!\[\]\(images/([^)\s]+)\)")
# 角标枚举 a) b) c) / (a) (b)：字母紧跟右括号 + 前置非字母/数字边界，
# 否则 (tension)/(compression) 等括号内单词尾部 "n)" 会被误计为角标；
# 数字前置排除 "see Figure 2a-d" 之类跨图引用产生的幻影角标
ENUM_RE = re.compile(r"(?<![a-z0-9])\(?([a-z])\)")
# 逗号成组枚举 d,e / d,e,f：组内逗号必须紧贴字母——"e.g., a" / "a) x, b)" 的
# 逗号后有空格故不成组（g / x 不会成为幻影角标）；组末字母后须是
# ) / 空白 / ; : ，。 . 等边界（覆盖 "d,e) ..."、"d,e ..."、"d,e." 三种收尾）
GROUP_RE = re.compile(r"(?<![a-z0-9])\(?([a-z](?:,[a-z])+)(?=[)\s;:，。.])")


def count_panels(caption: str) -> int:
    """统计图注中的子图角标数（a–f 范围 / a) b) 枚举 / d,e 枚举 / 无角标=1）。

    规则：收集所有单字母角标及其范围后缀，展开成集合去重。
    例: "a–f) ...; g) ...; h) ..." -> 8；"d,e) ..." -> 2；"no panels" -> 1。
    """
    if not caption:
        return 1
    panels: set[str] = set()
    # 范围写法 a–f / a-f / a–c
    for m in re.finditer(r"(?<![a-z0-9])([a-z])\s*[–\-—]\s*([a-z])", caption, re.IGNORECASE):
        s, e = m.group(1).lower(), m.group(2).lower()
        if s <= e:
            panels.update(chr(c) for c in range(ord(s), ord(e) + 1))
    # 枚举角标 a) b) c)（含 (a) 圆括号写法）
    for m in ENUM_RE.finditer(caption):
        panels.add(m.group(1).lower())
    # 逗号成组枚举 d,e / d,e,f（跨段累加，集合去重）
    for m in GROUP_RE.finditer(caption):
        for c in m.group(1):
            if "a" <= c <= "z":
                panels.add(c)
    # 罗马数字子项角标（i) ii) iii) iv) vi) 等）——caption 中存在长度>1 的
    # 罗马序列时，独立 i)/v)/x) 是罗马子项而非面板角标（P9 Fig1/Fig8 实测），
    # 从集合移除单字母 i/v/x（无罗马序列时仍按普通角标计）
    if re.search(r"(?<![a-z0-9])[ivx]{2,}\)", caption, re.IGNORECASE):
        panels.difference_update("ivx")
    return len(panels) if panels else 1


def parse_full_md(md_text: str) -> dict[int, dict]:
    """解析 full.md：每个 Figure 的 图注子图数 + 归属图片链接。

    返回 {fig_no: {"caption": str, "panels": int, "links": [hash.jpg]}}。
    归属铁律：图片链接归属其后最近的 Figure caption（MinerU 图片先于图注出现）。
    首个 caption 前的链接自然归属首个 figure；末个 caption 后的链接归属
    文档序最后一个 caption 的 figure。限制：图注跨行时仅统计 caption 首行角标。
    """
    lines = md_text.split("\n")
    figs: dict[int, dict] = {}
    last_cap_no: int | None = None
    pending: list[str] = []
    for ln in lines:
        m = CAP_RE.match(ln.strip())
        if m:
            no = int(m.group(1))
            figs[no] = {"caption": ln.strip(), "panels": count_panels(ln), "links": pending}
            pending = []
            last_cap_no = no
            continue
        for im in IMG_RE.finditer(ln):
            pending.append(im.group(1))
    # 末个 caption 之后的链接归文档序最后一个 figure（与首 caption 前图片的归属对称）
    if pending and last_cap_no is not None and last_cap_no in figs:
        figs[last_cap_no]["links"] += pending
    return figs


def evaluate(figs: dict[int, dict]) -> None:
    """比对 panels vs links 数，写 status/reason。"""
    for f in figs.values():
        n_links = len(f["links"])
        if n_links == f["panels"]:
            f["status"], f["reason"] = "OK", ""
        elif n_links > f["panels"]:
            f["status"], f["reason"] = "疑似", f"链接多（{n_links} > 图注 {f['panels']}，疑混入其他 figure 子图）"
        else:  # n_links < f["panels"]
            f["status"], f["reason"] = "疑似", f"链接少（{n_links} < 图注 {f['panels']}，疑合并/缺图）"


def main(raw_dir: str) -> int:
    raw = Path(raw_dir)
    md = raw / "full.md"
    if not md.is_file():
        print(f"fig_health: 无 {md}，跳过", file=sys.stderr)
        return 0
    md_text = md.read_text(encoding="utf-8")
    figs = parse_full_md(md_text)
    evaluate(figs)
    n_imgs = len(IMG_RE.findall(md_text))
    lines = ["# 拆图健康报告（fig_health.py）", "",
             "| Figure | 图注子图数 | 图片链接数 | 状态 | 原因 |",
             "|---|---|---|---|---|"]
    for no in sorted(figs):
        f = figs[no]
        lines.append(f"| Fig{no} | {f['panels']} | {len(f['links'])} | {f['status']} | {f['reason']} |")
    if not figs and n_imgs:
        warn = f"有图无图注（疑似解析异常）：{n_imgs} 张图未归属"
        lines.append("")
        lines.append(f"**{warn}**")
        print(f"fig_health: {warn}", file=sys.stderr)
    out = raw / "fig_health.md"
    # 覆写前备份旧报告（含 fig_verify 追加的纠正记录段），避免被抹掉
    if out.is_file():
        out.replace(raw / "fig_health.prev.md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    suspects = [no for no, f in figs.items() if f["status"] == "疑似"]
    print(f"fig_health: {len(figs)} figures, 疑似 {len(suspects)}: {suspects} -> {out.name}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
