#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""md2htmlnote helper: convert local relative image paths to fully-qualified URLs.

MinerU's official API / MCP (precision mode) exports a local `full.md` + `images/`
directory in which images are referenced by RELATIVE paths:

    ![](images/a8ecda1c....jpg)

These break in the generated HTML unless converted first. This helper rewrites
every `![...](images/xxx)` reference to `![...](<BASE_URL>/xxx)`, where
BASE_URL is a user-selected fully-qualified prefix ending in images (see
references/common.md, "Local images and optional online copies").

Usage:
    python link_images.py <input.md> <BASE_URL> [-o <output.md>]

Examples:
    python link_images.py full.md \
      "https://example.org/user-selected-archive/images" \
      -o linked.md

    # in-place overwrite when no -o is given:
    python link_images.py full.md "https://example.com/path/images"

Notes:
- Only `images/<name>` (relative, in an `images/` subdir) references are rewritten.
  Absolute URLs (https://...) and other paths are left untouched.
- Prints the count of replaced references and any leftover relative refs.
"""

import argparse
import re
import sys

REL_REF = re.compile(r"!\[([^\]]*)\]\(images/([^)]+)\)")


def convert(md: str, base_url: str) -> tuple[str, int, int]:
    def repl(m):
        alt, name = m.group(1), m.group(2)
        return f"![{alt}]({base_url}/{name})"

    new, n = REL_REF.subn(repl, md)
    leftover = len(re.findall(r"!\[[^\]]*\]\(images/[^)]+\)", new))
    return new, n, leftover


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="source markdown (MinerU export)")
    ap.add_argument("base_url", help="fully-qualified URL prefix up to and including the images dir, e.g. .../P5_x/images")
    ap.add_argument("-o", "--output", help="output markdown path (default: overwrite input)")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        md = f.read()

    new, n, leftover = convert(md, args.base_url.rstrip("/"))
    out = args.output or args.input
    with open(out, "w", encoding="utf-8") as f:
        f.write(new)

    print(f"replaced: {n} relative image refs")
    print(f"leftover relative refs: {leftover}")
    print(f"output: {out}")
    return 0 if leftover == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
