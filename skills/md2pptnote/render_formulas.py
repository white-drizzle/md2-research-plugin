#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""render_formulas.py — md2pptnote 公式渲染管线（xelatex 完整 LaTeX）。

输入 formulas.json，输出 PNG@600DPI + manifest.json。使用本地工具管线：
xelatex(standalone) → pdfcrop → pdftoppm -r 600。

formulas.json schema:
    [{"id": "f10", "latex": "t(\\tau) = ...", "mode": "display", "fg_color": "1A1A1A"}]
    - id:       唯一标识，作为文件名 stem（assets/figures/formulas/<id>.png）
    - latex:    raw LaTeX（JSON 双反斜杠转义）
    - mode:     display（\[...\]）/ inline（$...$）/ paragraph（裸 LaTeX，可含 minipage）
    - fg_color: 6 位 hex 前景色，默认 1A1A1A（不写 #）

用法: python render_formulas.py <formulas.json> [--outdir <assets/figures/formulas>]
输出: <outdir>/<id>.png + <outdir>/manifest.json（含宽高/aspect/error）
幂等: 产物存在且 latex 未变更（md5 缓存）则跳过。
编译失败条目记入 manifest 的 error 字段，不阻断整批（exit 0 但打印警告）。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Discover the user's local tools; never fall back to another machine's install.
XELATEX = shutil.which("xelatex") or "xelatex"
PDFCROP = shutil.which("pdfcrop") or "pdfcrop"
PDFTOPPM = shutil.which("pdftoppm") or "pdftoppm"

# 渲染管线版本：变更渲染命令（如 pdftoppm 参数）时必须递增，使缓存失效重渲
RENDER_VERSION = "transp-v2"

TEMPLATE = r"""\documentclass[border=4pt]{{standalone}}
\usepackage{{amsmath}}
\usepackage{{amsfonts}}
\usepackage{{xcolor}}
\definecolor{{fgcolor}}{{HTML}}{{{fg_color}}}
\begin{{document}}
\color{{fgcolor}}
{body}
\end{{document}}
"""


def _wrap(latex: str, mode: str) -> str:
    if mode == "inline":
        return f"${latex}$"
    if mode == "display":
        # standalone 文档类 body 在 \hbox 中，\[...\] 会报 Missing $——用
        # $\displaystyle ...$ 达到 display 排版效果（standalone 标准做法）
        return f"$\\displaystyle {latex}$"
    return latex  # paragraph: 用户自己控制 minipage/\\text 等结构


def _tex_source(latex: str, mode: str, fg: str) -> str:
    return TEMPLATE.format(fg_color=fg, body=_wrap(latex, mode))


def _hash_of(entry: dict) -> str:
    key = f"{RENDER_VERSION}|{entry.get('latex', '')}|{entry.get('mode', 'display')}|{entry.get('fg_color', '1A1A1A')}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def _read_png_size(path: Path) -> tuple[int, int] | None:
    """返回可读 PNG 尺寸；损坏/空文件返回 None。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.load()
            width, height = im.size
        return (width, height) if width > 0 and height > 0 else None
    except Exception:
        return None


def _make_transparent(png: Path) -> None:
    """白底 PNG → 透明背景：亮度 >245 置 alpha=0，200–245 渐变过渡（防抗锯齿白边）。"""
    from PIL import Image
    im = Image.open(png).convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if lum > 245:
                px[x, y] = (r, g, b, 0)
            elif lum > 200:
                px[x, y] = (r, g, b, int(255 * (245 - lum) / 45))
    im.save(png)


def _render_one(entry: dict, outdir: Path) -> dict:
    """渲染单条公式，返回 manifest 条目。"""
    fid = entry["id"]
    if not isinstance(fid, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", fid):
        return {"error": "id 只能包含字母、数字、下划线和连字符"}
    latex = entry["latex"]
    mode = entry.get("mode", "display")
    fg = entry.get("fg_color", "1A1A1A").lstrip("#")
    out_png = outdir / f"{fid}.png"

    with tempfile.TemporaryDirectory(prefix="frm_") as tmp:
        tmp = Path(tmp)
        tex = tmp / "formula.tex"
        tex.write_text(_tex_source(latex, mode, fg), encoding="utf-8")

        r = subprocess.run([XELATEX, "-interaction=nonstopmode",
                            "-output-directory", str(tmp), str(tex)],
                           capture_output=True, text=True, errors="replace",
                           timeout=120, cwd=str(tmp))
        pdf = tmp / "formula.pdf"
        if r.returncode != 0 or not pdf.exists():
            err = (r.stdout or "")[-600:] or r.stderr[:600]
            return {"error": err[:200].strip()}

        cropped = tmp / "cropped.pdf"
        r = subprocess.run([PDFCROP, str(pdf), str(cropped)],
                           capture_output=True, text=True, errors="replace", timeout=60)
        if not cropped.exists():
            cropped = pdf  # pdfcrop 失败时直接用原 PDF

        # pdftoppm 25.x 无 -transp 选项；白底转透明由 _make_transparent 在 PNG 上处理
        r = subprocess.run([PDFTOPPM, "-png", "-r", "600", str(cropped), str(tmp / "f")],
                           capture_output=True, text=True, errors="replace", timeout=120)
        page1 = tmp / "f-1.png"
        if not page1.exists():
            return {"error": "pdftoppm 无输出"}
        _make_transparent(page1)
        shutil.copy2(page1, out_png)

    try:
        from PIL import Image
        im = Image.open(out_png)
        w, h = im.size
    except Exception:
        w, h = 0, 0
    return {
        "file": f"assets/figures/formulas/{fid}.png",
        "width_px": w,
        "height_px": h,
        "aspect": round(w / h, 3) if h else 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("formulas", type=Path, help="formulas.json 路径")
    ap.add_argument("--outdir", type=Path, default=None,
                    help="输出目录（默认 formulas.json 同目录下 assets/figures/formulas）")
    args = ap.parse_args()

    entries = json.loads(args.formulas.read_text(encoding="utf-8"))
    if args.outdir:
        outdir = args.outdir
    else:
        outdir = args.formulas.parent / "assets" / "figures" / "formulas"
    outdir.mkdir(parents=True, exist_ok=True)

    # 幂等缓存：.cache.json {id: hash}，hash 相同且 PNG 存在则跳过
    cache_path = outdir / ".cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    manifest = {}
    todo = []
    for e in entries:
        fid = e["id"]
        h = _hash_of(e)
        png = outdir / f"{fid}.png"
        if (not isinstance(fid, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", fid)):
            todo.append(e)
            continue
        size = _read_png_size(png) if cache.get(fid) == h and png.exists() else None
        if size:
            width, height = size
            manifest[fid] = {"file": f"assets/figures/formulas/{fid}.png",
                             "width_px": width, "height_px": height,
                             "aspect": round(width / height, 3), "cached": True}
            continue
        cache.pop(fid, None)
        todo.append(e)

    errors = 0
    for e in todo:
        fid = e["id"]
        res = _render_one(e, outdir)
        if "error" in res:
            errors += 1
            print(f"  ✗ {fid}: {res['error']}", file=sys.stderr)
        else:
            print(f"  ✓ {fid}: {res['width_px']}x{res['height_px']} aspect={res['aspect']}")
        manifest[fid] = res
        if "error" in res:
            cache.pop(fid, None)
            if isinstance(fid, str) and re.fullmatch(r"[A-Za-z0-9_-]+", fid):
                (outdir / f"{fid}.png").unlink(missing_ok=True)
        else:
            cache[fid] = _hash_of(e)

    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"渲染完成: {len(todo) - errors}/{len(todo)} 成功, {errors} 失败, "
          f"{len(entries) - len(todo)} 缓存跳过 → {outdir}")
    if errors:
        print("存在失败条目，请修复 formulas.json 中的 latex 后重跑（见 manifest.json error 字段）",
              file=sys.stderr)
    return 0  # 失败不阻断整批（设计：manifest 记 error，agent 修复或回退）


if __name__ == "__main__":
    sys.exit(main())
