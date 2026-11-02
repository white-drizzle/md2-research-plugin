#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage MinerU output into the repo's reading-notes/<slug>/ directory.

Usage: python stage_to_repo.py <output_dir> <repo_root> <slug>

Replaces bash `mkdir -p` / `cp` / `cp -r` (not portable to a stripped PATH).
"""

import re
import shutil
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    if not re.fullmatch(r"[A-Za-z0-9_\-\u4e00-\u9fff]+", sys.argv[3]):
        print(f"ERROR: slug 含非法字符: {sys.argv[3]!r}", file=sys.stderr)
        return 1
    out = Path(sys.argv[1])
    repo = Path(sys.argv[2])
    slug = sys.argv[3]
    if not (out / "full.md").is_file() or not (out / "images").is_dir():
        print(f"ERROR: {out} 缺少 full.md 或 images/（需先完成 MinerU 解析）", file=sys.stderr)
        return 1
    dest = repo / "reading-notes" / slug
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out / "full.md", dest / "full.md")
    img_dest = dest / "images"
    if img_dest.exists():
        shutil.rmtree(img_dest)
    img_dest.mkdir()
    src_imgs = out / "images"
    for f in sorted(src_imgs.iterdir()):
        if f.is_file():
            shutil.copy2(f, img_dest / f.name)
    n = len(list(img_dest.iterdir()))
    print(f"staged full.md + {n} images -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
