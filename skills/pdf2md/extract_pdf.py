# -*- coding: utf-8 -*-
"""MinerU 精准解析 (SDK fallback): PDF -> full.md + images/ (本地保存, 相对路径, 无 CDN).

pdf2md skill Step 1 的备用路径——当 `mineru` MCP server 未加载时使用。
需要: pip install mineru-open-sdk; 环境变量 MINERU_TOKEN=<sk-...>

用法:
    set MINERU_TOKEN=sk-...
    python extract_pdf.py "<PDF绝对路径>" "<输出raw目录>"

输出: <输出目录>/full.md + <输出目录>/images/*.jpg
"""
import os
import sys


def main(pdf: str, out_dir: str) -> int:
    from mineru import MinerU

    token = os.environ.get("MINERU_TOKEN", "")
    if not token:
        print("ERROR: 缺少 MINERU_TOKEN 环境变量", file=sys.stderr)
        return 1

    client = MinerU(token=token)
    try:
        result = client.extract(pdf, model="pipeline", language="ch", timeout=600)
        print(f"state={result.state} err={result.error or ''} filename={result.filename}")
        if result.state != "done":
            return 1
        md_path = os.path.join(out_dir, "full.md")
        result.save_markdown(md_path, with_images=True)
        print(f"markdown saved: {md_path}")
        img_dir = os.path.join(out_dir, "images")
        if os.path.isdir(img_dir):
            print(f"images saved: {len(os.listdir(img_dir))} files")
            for f in sorted(os.listdir(img_dir))[:5]:
                print("  -", f)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
