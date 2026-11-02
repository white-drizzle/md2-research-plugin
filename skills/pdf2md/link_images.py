#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pdf2md helper: convert local relative image paths to fully-qualified URLs (or embed base64).

MinerU's official API / MCP (precision mode) exports a local `full.md` + `images/`
directory in which images are referenced by RELATIVE paths:

    ![](images/a8ecda1c....jpg)

These break in the generated HTML unless converted first. Two modes:

1. URL mode (default): rewrite every `![...](images/xxx)` reference to
   `![...](<BASE_URL>/xxx)`, where BASE_URL is a fully-qualified prefix
   (typically a GitHub raw URL, SKILL.md Step 3).
2. Embed mode (--embed, RECOMMENDED since 2026-08-16): rewrite every
   `![...](images/xxx)` to `![...](data:image/<mime>;base64,...)` — the output
   linked.md is fully self-contained (no GitHub push, no CDN, no network).

Usage:
    python link_images.py <input.md> <BASE_URL|images-dir> [-o <output.md>] [--embed]

Examples:
    # URL mode (legacy / shareable GitHub hosting)
    python link_images.py full.md \
      "https://example.org/user-selected-archive/images" \
      -o linked.md

    # Embed mode (self-contained; images resolved from ./images relative to input.md)
    python link_images.py full.md ./images --embed -o linked.md

Notes:
- Only `images/<name>` (relative, in an `images/` subdir) references are rewritten.
  Absolute URLs (https://...) and other paths are left untouched.
- Embed mode: images are read from <input.md's dir>/images/ (or the 2nd arg
  treated as a directory). Missing local image => reference kept + leftover count
  (exit 1), same gate semantics as URL mode.
- Prints the count of replaced references and any leftover relative refs.
- Exit code 0 iff no leftover relative refs remain (used as a gate in the skill).
"""

import argparse
import base64
import os
import re
import sys

REL_REF = re.compile(r"!\[([^\]]*)\]\(images/([^)]+)\)")


def _mime(name: str) -> str:
    ext = os.path.splitext(name)[1].lstrip(".").lower()
    return "jpeg" if ext in ("jpg", "jpeg") else ext or "octet-stream"


def convert(md: str, base_url: str) -> tuple[str, int, int]:
    def repl(m):
        alt, name = m.group(1), m.group(2)
        return f"![{alt}]({base_url}/{name})"

    new, n = REL_REF.subn(repl, md)
    leftover = len(re.findall(r"!\[[^\]]*\]\(images/[^)]+\)", new))
    return new, n, leftover


def convert_embed(md: str, images_dir: str) -> tuple[str, int, int]:
    """把 images/<name> 引用替换为 base64 data URI；缺图保留原引用并计入 leftover。"""
    img_root = images_dir
    replaced = 0

    def repl(m):
        nonlocal replaced
        alt, name = m.group(1), m.group(2)
        p = os.path.join(img_root, name)
        if not os.path.isfile(p):
            return m.group(0)  # 缺图：保留原引用（计入 leftover）
        data = base64.b64encode(open(p, "rb").read()).decode("ascii")
        replaced += 1
        return f"![{alt}](data:image/{_mime(name)};base64,{data})"

    new, _n = REL_REF.subn(repl, md)
    leftover = len(re.findall(r"!\[[^\]]*\]\(images/[^)]+\)", new))
    return new, replaced, leftover


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="source markdown (MinerU export)")
    ap.add_argument("base", help="URL prefix (URL mode) or local images dir (embed mode)")
    ap.add_argument("-o", "--output", help="output markdown path (default: overwrite input)")
    ap.add_argument("--embed", action="store_true",
                    help="embed mode: images/<name> -> data:image/...;base64 (self-contained)")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        md = f.read()

    if args.embed:
        # base 参数 = 图片所在目录（兼容传 full.md 同目录下的 images/ 或 raw/images）
        new, n, leftover = convert_embed(md, args.base.rstrip("/\\"))
        mode = "embed"
    else:
        new, n, leftover = convert(md, args.base.rstrip("/"))
        mode = "url"

    out = args.output or args.input
    with open(out, "w", encoding="utf-8") as f:
        f.write(new)

    print(f"replaced: {n} relative image refs ({mode})")
    print(f"leftover relative refs: {leftover}")
    print(f"output: {out}")
    return 0 if leftover == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
