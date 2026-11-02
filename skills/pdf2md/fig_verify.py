# fig_verify.py（疑似拆图视觉核验 + HTML img src 自动重写 + 修正版输入链物化）
# -*- coding: utf-8 -*-
"""Generate contact sheets for primary-model review and apply explicit figure mappings.

Usage:
  python fig_verify.py <raw> [<html>]                         # contact sheets + blank mapping
  python fig_verify.py <raw> [<html>] --dump                  # same as the default
  python fig_verify.py <raw> [<html>] --apply <mapping.json>  # apply reviewed labels

Read the numbered contact sheets with the primary multimodal model and fill the
JSON mapping with single-letter panel labels. Leave merged/uncertain panels blank
or "?"; an empty mapping fails without rewriting inputs. No external vision API
is used. Explicit --apply can rewrite HTML and materialize full_fixed.md and
linked_fixed.md with MANIFEST registration; full.md and linked.md stay unchanged.
"""
import base64
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import fig_health

LINK_IMAGES = Path(__file__).resolve().parent / "link_images.py"
PY = sys.executable






def rewrite_md(md_text: str, fig_mappings: dict[int, dict[str, str]]) -> tuple[str, bool]:
    """按 {fig_no: {hash: 角标字母}} 重排 full.md 各 figure 块内图片链接顺序。

    归属与 fig_health 同规则（图片链接归属其后最近 caption）；只重排映射覆盖的
    链接（合并/未判定项保持相对位置）。返回 (新文本, 是否变化)。
    """
    lines = md_text.split("\n")
    pending: list[tuple[int, int, int, str]] = []  # (行号, start, end, hash)
    spans_by_fig: dict[int, list] = {}
    for i, ln in enumerate(lines):
        m = fig_health.CAP_RE.match(ln.strip())
        if m:
            spans_by_fig[int(m.group(1))] = pending
            pending = []
            continue
        for im in fig_health.IMG_RE.finditer(ln):
            pending.append((i, im.start(), im.end(), im.group(1)))
    changed = False
    for no, mapping in fig_mappings.items():
        spans = spans_by_fig.get(no) or []
        current = [h for *_, h in spans]
        pairs = sorted(((mapping[h], h) for h in current if h in mapping), key=lambda kv: kv[0])
        if not pairs:
            continue
        desired = [h for _, h in pairs] + [h for h in current if h not in mapping]
        if desired == current:
            continue
        by_line: dict[int, list] = {}
        for (i, s, e, _h), new_h in zip(spans, desired):
            by_line.setdefault(i, []).append((s, e, new_h))
        for i, items in by_line.items():  # 同行自右向左替换，防偏移
            for s, e, new_h in sorted(items, key=lambda t: t[0], reverse=True):
                lines[i] = lines[i][:s] + f"![](images/{new_h})" + lines[i][e:]
        changed = True
    return "\n".join(lines), changed


def materialize_fixed(raw: Path, fixed_text: str, paper: str) -> list[str]:
    """物化修正版输入链：full_fixed.md + linked_fixed.md + MANIFEST 幂等 upsert。"""
    notes: list[str] = []
    fixed_md = raw / "full_fixed.md"
    fixed_linked = raw / "linked_fixed.md"
    hdr = (f"<!-- {paper}/full_fixed.md — full.md 的图序/缺图纠正版"
           f"（原件 full.md 不变；纠正记录见 raw/fig_health.md）。生成 "
           f"{datetime.date.today().isoformat()} -->\n\n")
    fixed_md.write_text(hdr + fixed_text, encoding="utf-8")
    notes.append(f"full_fixed.md 已物化（{len(fixed_text)} 字符）")
    r = subprocess.run([PY, str(LINK_IMAGES), str(fixed_md), str(raw / "images"),
                        "--embed", "-o", str(fixed_linked)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        notes.append(f"linked_fixed.md 生成失败（exit {r.returncode}）: {(r.stderr or r.stdout)[-200:]}")
        return notes
    notes.append("linked_fixed.md 已生成（base64）")
    root = raw.parent.parent.parent  # <project>/_tmp/P<n>/raw -> <project>
    mf = root / "_tmp" / "MANIFEST.json"
    if not mf.is_file():
        notes.append("未找到 _tmp/MANIFEST.json，跳过登记")
        return notes
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
        for p in data.get("papers", []):
            if p.get("id") == paper:
                p["full_fixed_md"] = f"_tmp/{paper}/raw/full_fixed.md"
                p["linked_fixed_md"] = f"_tmp/{paper}/raw/linked_fixed.md"
        mf.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        notes.append("MANIFEST 已更新（full_fixed_md / linked_fixed_md）")
    except Exception as exc:  # noqa: BLE001 — 登记失败不影响纠正主流程
        notes.append(f"MANIFEST 更新失败: {exc}")
    return notes


REWRITE_PAT = re.compile(
    r'(<img\b[^>]*?src="data:image/[^"]*?base64,)([^"]+)("[^>]*?alt=")(Fig\s*\d+[^"]*)("[^>]*?>)'
)
REWRITE_PAT2 = re.compile(
    r'(<img\b[^>]*?alt=")(Fig\s*\d+[^"]*)("[^>]*?src="data:image/[^"]*?base64,)([^"]+)("[^>]*?>)'
)
# alt 结构解析："Fig 7a" -> fig=7, panel=a；"Fig 1"（整图无角标）panel 为空
ALT_RE = re.compile(r"(\d+)\s*([a-z]?)$", re.IGNORECASE)


def rewrite_html(html: str, mapping: dict[str, str], imgdir: Path,
                 alt_prefix: str, fig_no: int | None = None) -> str:
    """按 mapping {hash.jpg: 角标字母} 重写 alt 以 alt_prefix 开头的 img src。

    mapping 决定每个角标应放哪张图：先按角标字母排序得到 {角标字母: hash}，
    再对每个 img 按其 alt 中图号+角标替换 src。缺图/无角标/无映射保留原样。
    fig_no 指定后只重写该图号对应的 img（防止映射泄漏到其他 figure 的同字母
    角标，如 Fig6 的 g/h 映射改写 Fig3g/Fig8g）；fig_no=None 时按角标字母
    全局匹配（供单 figure 场景/测试使用）。替换只改 base64 数据本身，
    保留 img 全部其他属性与 MIME 前缀。
    """
    ordered = {label: h for h, label in sorted(mapping.items(), key=lambda kv: kv[1])}

    def repl(m, alt_idx, src_idx, alt_first):
        alt = m.group(alt_idx).strip()
        if not alt.startswith(alt_prefix):
            return m.group(0)
        am = ALT_RE.search(alt[len(alt_prefix):])
        if not am:
            return m.group(0)
        panel = am.group(2).lower()
        if not panel:
            return m.group(0)
        if fig_no is not None and int(am.group(1)) != fig_no:
            return m.group(0)
        h = ordered.get(panel)
        if not h:
            return m.group(0)
        p = imgdir / h
        if not p.is_file():
            return m.group(0)
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        if alt_first:
            # PAT2（alt 在前）: g1=<img...alt="  g2=alt文本  g3=...src=前缀  g4=src数据
            return f"{m.group(1)}{alt}{m.group(3)}{data}{m.group(5)}"
        # PAT（src 在前）: g1=<img...src=前缀  g2=src数据  g3=...alt="  g4=alt文本
        return f"{m.group(1)}{data}{m.group(3)}{alt}{m.group(5)}"

    html = REWRITE_PAT.sub(lambda m: repl(m, 4, 2, False), html)
    html = REWRITE_PAT2.sub(lambda m: repl(m, 2, 4, True), html)
    return html


def apply_mappings(raw: Path, html_path: str, fig_mappings: dict[int, dict[str, str]],
                   channel: str = "fig_verify", extra_notes: list[str] | None = None) -> int:
    """应用映射：修正版物化（full_fixed/linked_fixed/manifest）+ HTML 重写 + 追加记录。"""
    imgdir = raw / "images"
    fixed_notes: list[str] = []
    md = raw / "full.md"
    if fig_mappings and md.is_file():
        md_text, md_changed = rewrite_md(md.read_text(encoding="utf-8"), fig_mappings)
        if md_changed:
            fixed_notes = materialize_fixed(raw, md_text, raw.parent.name)
            for n in fixed_notes:
                print("fig_verify:", n)
    rewritten = False
    if html_path:
        html_file = Path(html_path)
        if not html_file.is_file():
            print(f"fig_verify: HTML 不存在（{html_path}），仅报告", file=sys.stderr)
        else:
            html = html_file.read_text(encoding="utf-8")
            # 逐 figure 重写（fig_no 限定图号，防止跨 figure 角标泄漏）
            new = html
            for no, mapping in sorted(fig_mappings.items()):
                new = rewrite_html(new, mapping, imgdir, "Fig ", fig_no=no)
            if new != html:
                html_file.write_text(new, encoding="utf-8")
                rewritten = True
                print(f"fig_verify: HTML 已重写（{html_file.name}）")
            else:
                print("fig_verify: HTML 无需重写（无可用映射或内容已一致）")
    else:
        print(f"fig_verify: 无 HTML 目标，映射 {fig_mappings}，仅报告")
    # 持久化：映射/备注/重写状态一律追加到 fig_health.md（不只 stdout）
    all_mapping: dict[str, str] = {}
    for m in fig_mappings.values():
        all_mapping.update(m)
    lines = ["", f"## 纠正记录（{channel}）", f"- 映射: {all_mapping}"]
    if extra_notes:
        lines += extra_notes
    if fixed_notes:
        lines.append("- 修正版物化:")
        lines += [f"  - {n}" for n in fixed_notes]
    lines.append("- 已触发重写" if rewritten else "- 未触发重写")
    with open(raw / "fig_health.md", "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return 0



SUSPECT_RE = re.compile(r"\|\s*Fig(\d+)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*疑似")


def _read_suspects(report: Path) -> list[int]:
    suspects = []
    for ln in report.read_text(encoding="utf-8").splitlines():
        m = SUSPECT_RE.match(ln)
        if m:
            suspects.append(int(m.group(1)))
    return suspects


def dump_suspects(raw: Path) -> int:
    """--dump：输出疑似 figure 清单 + 带编号接触表 + 空映射模板（供主模型 Read 后填写）。"""
    report = raw / "fig_health.md"
    if not report.is_file():
        print("fig_verify: 无 fig_health.md，先跑 fig_health", file=sys.stderr)
        return 1
    suspects = _read_suspects(report)
    if not suspects:
        print("fig_verify: 无疑似 figure，无需核验")
        return 0
    md = raw / "full.md"
    if not md.is_file():
        print(f"fig_verify: 无 {md}，未生成接触表", file=sys.stderr)
        return 1
    figs = fig_health.parse_full_md(md.read_text(encoding="utf-8"))
    import tempfile
    from PIL import Image, ImageDraw
    imgdir = raw / "images"
    outdir = Path(tempfile.mkdtemp(prefix="fig_verify_dump_"))
    template: dict[str, dict[str, str]] = {}
    for no in suspects:
        f = figs.get(no)
        if not f or not f["links"]:
            print(f"fig_verify: Fig{no} 无图链接，跳过")
            continue
        print(f"\n== Fig{no} ==\n图注: {f['caption']}")
        cells = []
        for idx, h in enumerate(f["links"], start=1):
            print(f"  [{idx}] {h}")
            if (imgdir / h).is_file():
                cells.append((idx, h))
        if not cells:
            continue
        cols = min(4, len(cells))
        rows = (len(cells) + cols - 1) // cols
        CELL = 420
        sheet = Image.new("RGB", (cols * CELL, rows * CELL), "white")
        d = ImageDraw.Draw(sheet)
        for i, (idx, h) in enumerate(cells):
            im = Image.open(imgdir / h).convert("RGB")
            im.thumbnail((CELL - 20, CELL - 50))
            x = (i % cols) * CELL
            y = (i // cols) * CELL
            sheet.paste(im, (x + 10, y + 40))
            d.text((x + 10, y + 8), f"Fig{no} [{idx}] {h[:8]}", fill="red")
        sp = outdir / f"fig{no}_contact.png"
        sheet.save(sp)
        print(f"  接触表: {sp}")
        template[str(no)] = {h: "" for _, h in cells}
    tmpl = outdir / "mapping_template.json"
    tmpl.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n映射模板: {tmpl}")
    print("下一步: Read 接触表 → 按图中角标语义填写每张图的字母（合并图/无法判定留空或 \"?\"）→ 运行:")
    print(f'  python fig_verify.py "{raw}" [<html>] --apply "{tmpl}"')
    return 0


def apply_mapping_file(raw: Path, html_path: str, mapping_path: str) -> int:
    """--apply：只应用人工或主模型已核验的单字母映射。"""
    p = Path(mapping_path)
    if not p.is_file():
        print(f"fig_verify: 映射文件不存在（{mapping_path}）", file=sys.stderr)
        return 1
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"fig_verify: 无法读取映射 JSON（{exc}），未做修改")
        return 1
    if not isinstance(data, dict):
        print("fig_verify: 映射必须是 {图号: {图片文件名: 角标}} 对象，未做修改")
        return 1
    fig_mappings: dict[int, dict[str, str]] = {}
    for k, m in data.items():
        if not k.isascii() or not k.isdigit() or int(k) < 1 or not isinstance(m, dict):
            print("fig_verify: 图号须为正整数且每图映射须为对象，未做修改")
            return 1
        if any(not isinstance(h, str) or not h or Path(h).name != h or h in {".", ".."}
               or not isinstance(v, str) for h, v in m.items()):
            print("fig_verify: 图片须为本地文件名且角标须为字符串，未做修改")
            return 1
        mm = {h: v.strip().lower() for h, v in m.items()
              if re.fullmatch(r"[a-z]", v.strip().lower())}
        if mm:
            fig_mappings[int(k)] = mm
    if not fig_mappings:
        print("fig_verify: 映射为空（未填任何角标字母），未做修改")
        return 1
    return apply_mappings(raw, html_path, fig_mappings, "fig_verify（agent 直读 --apply）")


def main(raw_dir: str, html_path: str = "", dump: bool = False, apply_path: str = "") -> int:
    raw = Path(raw_dir)
    if dump:
        return dump_suspects(raw)
    if apply_path:
        return apply_mapping_file(raw, html_path, apply_path)
    return dump_suspects(raw)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    raw_dir, html_path, dump_mode, apply_path = args[0], "", False, ""
    rest = args[1:]
    if rest and not rest[0].startswith("-"):
        html_path = rest.pop(0)
    while rest:
        a = rest.pop(0)
        if a == "--dump":
            dump_mode = True
        elif a == "--apply" and rest:
            apply_path = rest.pop(0)
        else:
            print(f"fig_verify: 未知参数 {a}", file=sys.stderr)
            sys.exit(2)
    sys.exit(main(raw_dir, html_path, dump_mode, apply_path))
