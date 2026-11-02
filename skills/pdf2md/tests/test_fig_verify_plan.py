# tests/test_fig_verify_plan.py
# -*- coding: utf-8 -*-
"""fig_verify.py 主模型映射应用与修正版输入链回归检查。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def test_python_is_sys_executable():
    import fig_verify
    assert fig_verify.PY == sys.executable


def test_read_suspects_parses_report():
    import tempfile, pathlib
    import fig_verify
    report = pathlib.Path(tempfile.mkdtemp()) / "fig_health.md"
    rows = [
        "| Figure | 图注子图数 | 图片链接数 | 状态 | 原因 |",
        "|---|---|---|---|---|",
        "| Fig1 | 2 | 2 | OK |  |",
        "| Fig3 | 1 | 0 | 疑似 | 链接少 |",
        "| Fig8 | 1 | 4 | 疑似 | 链接多 |",
    ]
    report.write_text("\n".join(rows) + "\n", encoding="utf-8")
    assert fig_verify._read_suspects(report) == [3, 8]


def test_apply_mapping_file_reorders_and_materializes():
    import json, tempfile, pathlib
    import fig_verify
    root = pathlib.Path(tempfile.mkdtemp())
    raw = root / "_tmp" / "P1" / "raw"
    (raw / "images").mkdir(parents=True)
    for h in ("a1.jpg", "a2.jpg", "b1.jpg", "b2.jpg", "b3.jpg"):
        (raw / "images" / h).write_bytes(b"x")
    md_lines = [
        "# Paper", "",
        "![](images/a1.jpg)", "",
        "![](images/a2.jpg)", "",
        "Fig. 1. cap.", "",
        "![](images/b1.jpg)", "",
        "![](images/b2.jpg)", "",
        "![](images/b3.jpg)", "",
        "Fig. 2. cap.", "",
    ]
    (raw / "full.md").write_text("\n".join(md_lines), encoding="utf-8")
    mp = root / "m.json"
    mp.write_text(json.dumps({"1": {"a2.jpg": "a", "a1.jpg": "b"},
                              "2": {"b3.jpg": "a", "b1.jpg": "b", "b2.jpg": "c"}}),
                  encoding="utf-8")
    rc = fig_verify.apply_mapping_file(raw, "", str(mp))
    assert rc == 0
    fixed = (raw / "full_fixed.md").read_text(encoding="utf-8")
    assert fixed.index("a2.jpg") < fixed.index("a1.jpg")
    assert fixed.index("b3.jpg") < fixed.index("b1.jpg") < fixed.index("b2.jpg")
    assert (raw / "linked_fixed.md").is_file()
    rec = (raw / "fig_health.md").read_text(encoding="utf-8")
    assert "agent 直读 --apply" in rec
    before = fixed
    assert fig_verify.apply_mapping_file(raw, "", str(mp)) == 0
    assert (raw / "full_fixed.md").read_text(encoding="utf-8") == before


def test_apply_mapping_file_empty_mapping_fails():
    import json, tempfile, pathlib
    import fig_verify
    root = pathlib.Path(tempfile.mkdtemp())
    raw = root / "_tmp" / "P1" / "raw"
    raw.mkdir(parents=True)
    (raw / "full.md").write_text("# x", encoding="utf-8")
    mp = root / "empty.json"
    mp.write_text(json.dumps({"1": {"a.jpg": ""}}), encoding="utf-8")
    assert fig_verify.apply_mapping_file(raw, "", str(mp)) == 1
