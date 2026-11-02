#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""save_version.py — deck 里程碑留档。

把一个 deck 工作目录的产物（slide_plan.json / final_presentation_cn.pptx / qa_report.md）
copy 进 <deck_dir>/versions/<标签>/，并在 _versions.md 清单追加一行。

用法: python save_version.py <deck_dir> <标签> [--note "改动要点"]
退出码: 0=成功, 1=标签已存在（除非 --force 覆盖）, 2=deck 目录不存在。
"""
import argparse
import os
import shutil
import sys
from datetime import date

# 会归档的产物
_ARCHIVE_FILES = ("slide_plan.json", "final_presentation_cn.pptx", "qa_report.md")


def save_version(deck_dir: str, label: str, note: str = "", force: bool = False) -> int:
    """把 deck 产物留档为版本。返回 0=成功 / 1=标签已存在 / 2=deck 目录不存在。"""
    if not os.path.isdir(deck_dir):
        print(f"[save_version] deck 目录不存在: {deck_dir}")
        return 2
    versions_dir = os.path.join(deck_dir, "versions")
    target = os.path.join(versions_dir, label)
    if os.path.exists(target):
        if not force:
            print(f"[save_version] 标签 {label} 已存在，未覆盖（用 force 覆盖）")
            return 1
        shutil.rmtree(target)
    os.makedirs(target, exist_ok=True)

    copied = []
    for f in _ARCHIVE_FILES:
        src = os.path.join(deck_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(target, f))
            copied.append(f)

    # 清单追加
    os.makedirs(versions_dir, exist_ok=True)
    manifest = os.path.join(versions_dir, "_versions.md")
    today = date.today().isoformat()
    line = f"- {label} | {today} | {note or '（无备注）'}"
    with open(manifest, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    print(f"[save_version] {label}: {', '.join(copied) or '（无产物）'} 已归档到 versions/{label}/")
    return 0


def main() -> int:
    """命令行入口：解析参数并调用 save_version。"""
    parser = argparse.ArgumentParser(description="deck 里程碑留档")
    parser.add_argument("deck_dir", help="deck 工作目录")
    parser.add_argument("label", help="版本标签，如 v1 / v2")
    parser.add_argument("--note", default="", help="改动要点")
    parser.add_argument("--force", action="store_true", help="标签已存在时强制覆盖")
    args = parser.parse_args()
    return save_version(args.deck_dir, args.label, args.note, args.force)


if __name__ == "__main__":
    sys.exit(main())
