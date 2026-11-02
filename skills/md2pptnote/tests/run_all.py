#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键跑全部测试：extract_figures / verify_plan / render2pptx / verify_pptx / save_version。

用法: python tests/run_all.py
退出码 0=全绿，1=有失败。
"""
import importlib
import sys
from pathlib import Path

TESTS = [
    "test_extract",
    "test_verify_plan",
    "test_render",
    "test_verify",
    "test_save_version",
    "test_render_formulas",
    "test_verify_contract",
]


def main() -> int:
    tests_dir = Path(__file__).parent
    sys.path.insert(0, str(tests_dir))
    total = failed = 0
    for mod in TESTS:
        m = importlib.import_module(mod)
        fns = [(name, fn) for name, fn in vars(m).items()
               if name.startswith("test_") and callable(fn)]
        for name, fn in fns:
            total += 1
            try:
                fn()
                print(f"  PASS {mod}.{name}")
            except Exception as exc:
                failed += 1
                print(f"  FAIL {mod}.{name}: {exc}")
    print(f"\n{total - failed}/{total} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
