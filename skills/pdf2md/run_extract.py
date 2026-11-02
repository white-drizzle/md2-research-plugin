#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MinerU 批量并行解析: PDFs -> <out_root>/P<编号>/raw/ (full.md + images).

后台批处理版 extract_pdf.py：一次提交多篇 PDF，并行调用 MinerU 云端解析
（默认 2 并发，避免触发云端限流），已解析过的（raw/full.md 存在）自动跳过
（缓存）。这样 P 系列文献管线可以把「等云端解析」这一步移到后台跑，
解析完成后由 harness 继续 link/stage/生成 后续步骤。

用法:
    python run_extract.py <out_root> <pdf1> <pdf2> ... [--workers N]

    <out_root>  产物根目录（约定 <project>\\_tmp），每篇生成
                <out_root>/P<编号>/raw/ (full.md + images/)
    <pdfN>      要解析的 PDF 绝对路径；文件名须含 P<编号>（如 P3-xxx.pdf）
    --workers   并行度，默认 2

Token 获取（按优先级）:
    1. 环境变量 MINERU_TOKEN（已 set 则用之）
    2. ~/.claude.json -> mcpServers.mineru.env.MINERU_API_TOKEN（自动读取）
    3. ~/.zcode/cli/config.json -> mcp.servers.mineru.env.MINERU_API_TOKEN（zcode 插件配置）

输出: 每篇状态 (done/skip/fail)，exit 0 当且仅当无 fail。
"""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import extract_pdf
import fig_health

P_NUM_RE = re.compile(r"P(\d+)[-_]", re.I)

_TOKEN_SOURCES = (
    # (配置文件, 定位 mineru token 的键路径)
    (os.path.expanduser("~/.claude.json"), ("mcpServers", "mineru", "env", "MINERU_API_TOKEN")),
    # zcode 插件 userConfig：plugins.options.<plugin>.<field>（实测 2026-08-16）
    (os.path.expanduser("~/.zcode/cli/config.json"),
     ("plugins", "options", "super-research-plugin@super-research-plugin", "mineru_api_token")),
    # zcode 显式 mcp 配置（老结构，兜底）
    (os.path.expanduser("~/.zcode/cli/config.json"), ("mcp", "servers", "mineru", "env", "MINERU_API_TOKEN")),
)


def _get_by_path(cfg: dict, keys: tuple):
    node = cfg
    for k in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(k)
    return node


def load_token() -> str:
    """MINERU_TOKEN env -> ~/.claude.json -> ~/.zcode/cli/config.json, whichever is set."""
    tok = os.environ.get("MINERU_TOKEN", "").strip()
    if tok:
        return tok
    for path, keys in _TOKEN_SOURCES:
        try:
            cfg = json.load(open(path, encoding="utf-8"))
            v = _get_by_path(cfg, keys)
            tok = v if isinstance(v, str) else ""
        except Exception:
            tok = ""
        if tok:
            return tok.strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_root", help="产物根目录（每篇 <out_root>/P<编号>/raw/）")
    ap.add_argument("pdfs", nargs="+", help="PDF 绝对路径（文件名须含 P<编号>）")
    ap.add_argument("--workers", type=int, default=2, help="并行度，默认 2")
    args = ap.parse_args()

    token = load_token()
    if not token:
        print("ERROR: 找不到 MinerU token（设 MINERU_TOKEN 或配置 ~/.claude.json）",
              file=sys.stderr)
        return 2
    os.environ["MINERU_TOKEN"] = token

    jobs = []  # (pid, pdf, raw_dir)
    for pdf in args.pdfs:
        base = os.path.basename(pdf)
        m = P_NUM_RE.search(base)
        if not m:
            print(f"WARN: 文件名不含 P<编号>，跳过: {base}", file=sys.stderr)
            continue
        pid = m.group(1)
        raw = os.path.join(args.out_root, f"P{pid}", "raw")
        jobs.append((pid, pdf, raw))

    if not jobs:
        print("ERROR: 没有可解析的 PDF", file=sys.stderr)
        return 2

    todo = [(pid, pdf, raw) for pid, pdf, raw in jobs
            if not os.path.isfile(os.path.join(raw, "full.md"))]
    skipped = len(jobs) - len(todo)
    print(f"jobs={len(jobs)} todo={len(todo)} skipped(缓存命中)={skipped} workers={args.workers}")

    results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(extract_pdf.main, pdf, raw): pid
                for pid, pdf, raw in todo}
        for fut in futs:
            pid = futs[fut]
            try:
                rc = fut.result()
            except Exception as e:  # noqa: BLE001 - 单篇失败不拖垮整批
                results[pid] = f"fail({e!r})"
                continue
            results[pid] = "done" if rc == 0 else f"fail(rc={rc})"

    # 拆图健康检查：解析成功与缓存命中（full.md 已存在）的篇目都跑 fig_health
    # （不阻断主流程）；失败计入汇总
    fh_fails = []
    for pid, _pdf, raw in jobs:
        if not os.path.isfile(os.path.join(raw, "full.md")):
            continue  # 解析失败/无产物，跳过
        try:
            fig_health.main(raw)
        except Exception as e:  # noqa: BLE001
            print(f"P{pid}: fig_health 失败({e!r})")
            fh_fails.append(f"P{pid}")

    print("---- 汇总 ----")
    fails = 0
    for pid, _pdf, _raw in jobs:
        st = results.get(pid, "skip(缓存)")
        print(f"P{pid}: {st}")
        if st.startswith("fail"):
            fails += 1
    if fh_fails:
        print(f"fig_health fail: [{', '.join(fh_fails)}]")
    print(f"---- done: {len(todo) - fails}/{len(todo)} 成功, skipped={skipped} ----")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
