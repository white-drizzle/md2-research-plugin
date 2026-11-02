# -*- coding: utf-8 -*-
"""embed_base64.py — 把 HTML 阅读笔记的图片引用内嵌为 base64 data URI（离线单文件，md2htmlnote 默认方案）。

处理对象：<img src="..."> 中所有非 data: 的 src——
  1. GitHub raw URL（https://raw.githubusercontent.com/.../images/<fname>）：从 --images-dir 取图
  2. 相对路径（如 raw/images/xx.jpg 或 images/xx.jpg）：先相对 HTML 所在目录解析，
     失败则取文件名到 --images-dir 下找（unquote 匹配）
替换为 data:image/<mime>;base64,...，img 标签其余属性（lightbox onclick/onerror 等）原样保留。
幂等：所有 img 已为 data: 时跳过不写。缺本地图则保留原引用并报告——默认残留外链即 exit 1
（门控），--allow-missing 可降级为 exit 0。

用法: python embed_base64.py <input.html> [-o <output.html>] [--images-dir <dir>] [--allow-missing]
"""
import argparse
import base64
import re
import urllib.parse
from pathlib import Path

# 匹配 raw URL 中的图片文件名；相对路径单独处理
RAW_FNAME_RE = re.compile(r"https://raw\.githubusercontent\.com/[^\"\s]*?/images/([^\"/]+)")
SRC_RE = re.compile(r'(<img\b[^>]*\bsrc=")([^"]+)(")')


def mime_of(path: Path) -> str:
    ext = path.suffix.lstrip(".").lower()
    return "jpeg" if ext in ("jpg", "jpeg") else ext or "octet-stream"


def resolve_local(src, html_dir: Path, images_dir):
    """src -> 本地图片路径；找不到返回 None。"""
    if src.startswith("http"):
        m = RAW_FNAME_RE.search(src)
        if not m:
            return None
        fname = urllib.parse.unquote(m.group(1))
    else:
        # 相对路径：HTML 同目录解析失败则按文件名去 images_dir 找
        fname = urllib.parse.unquote(src.split("/")[-1])
        p = (html_dir / src).resolve()
        if p.is_file():
            return p
    if images_dir is not None:
        for base in (images_dir, images_dir / "images"):
            p = base / fname
            if p.is_file():
                return p
    return None


def embed(html_path: Path, images_dir, allow_missing: bool) -> tuple:
    """返回 (changed_count, residual_srcs, missing_srcs)。"""
    html = html_path.read_text(encoding="utf-8")
    if "data:image" in html and not re.search(r'<img\b[^>]*\bsrc="(?!data:)', html):
        return 0, [], []  # 已全内嵌，幂等跳过

    html_dir = html_path.parent
    changed, missing = [], []
    seen = set()  # 防止同一 src 重复计数/重复替换

    def repl(m):
        prefix, src, suffix = m.group(1), m.group(2), m.group(3)
        if src.startswith("data:") or src in seen:
            return m.group(0)
        seen.add(src)
        local = resolve_local(src, html_dir, images_dir)
        if local is None:
            missing.append(src)
            return m.group(0)  # 保留原引用
        data = base64.b64encode(local.read_bytes()).decode("ascii")
        changed.append(src)
        return f'{prefix}data:image/{mime_of(local)};base64,{data}{suffix}'

    new_html = SRC_RE.sub(repl, html)
    if new_html != html:
        html_path.write_text(new_html, encoding="utf-8")
    # 残留外链 = 转换后 HTML 中仍非 data: 的 src（缺图被保留的引用）
    residual = [s for s in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', new_html)
                if not s.startswith("data:")]
    return len(changed), residual, missing


def main():
    ap = argparse.ArgumentParser(description="内嵌 HTML 图片为 base64 data URI（离线单文件）")
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=None, help="输出路径（默认就地覆盖）")
    ap.add_argument("--images-dir", type=Path, default=None,
                    help="本地图片目录（raw/images 等）；缺省按 HTML 相对路径解析")
    ap.add_argument("--allow-missing", action="store_true", help="缺图降级为 exit 0")
    args = ap.parse_args()

    html_path = args.input
    out_path = args.output or html_path
    # 输出到新路径时先复制，保证就地/异位逻辑一致
    if out_path.resolve() != html_path.resolve():
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(html_path.read_bytes())
        html_path = out_path
    if not html_path.is_file():
        print(f"FAIL: 文件不存在 {html_path}")
        return 2

    changed, residual, missing = embed(html_path, args.images_dir, args.allow_missing)
    size_kb = html_path.stat().st_size // 1024
    print(f"转换报告: {html_path.name} 内嵌 {changed} 张图 -> {size_kb} KB")
    for s in missing:
        print(f"  ! 缺本地图，保留原引用: {s[:100]}")
    if residual:
        print(f"  ! 残留 {len(residual)} 处外链引用（缺图/错位）")
        if not args.allow_missing:
            print("FAIL: 残留外链——先补齐本地图片（check_image_refs.py 可定位），或 --allow-missing 降级")
            return 1
    print("PASS" if not residual or args.allow_missing else "FAIL")
    return 0 if (not residual or args.allow_missing) else 1


if __name__ == "__main__":
    raise SystemExit(main())
