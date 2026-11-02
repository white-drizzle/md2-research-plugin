# -*- coding: utf-8 -*-
"""save_version.py 测试：里程碑留档 + 版本清单。"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "slides"))
import save_version as sv


def _make_deck(td: str) -> str:
    """造一个最小的 deck 工作目录。"""
    deck = os.path.join(td, "deck")
    os.makedirs(os.path.join(deck, "assets", "figures"), exist_ok=True)
    # 三个会被归档的产物
    Path(os.path.join(deck, "slide_plan.json")).write_text('{"slides": []}', encoding="utf-8")
    Path(os.path.join(deck, "final_presentation_cn.pptx")).write_text("pptx-bytes", encoding="utf-8")
    Path(os.path.join(deck, "qa_report.md")).write_text("# QA", encoding="utf-8")
    return deck


def test_save_creates_version_subdir_and_copies():
    with tempfile.TemporaryDirectory() as td:
        deck = _make_deck(td)
        v = sv.save_version(deck, "v1")
        assert v == 0
        vdir = os.path.join(deck, "versions", "v1")
        assert os.path.isdir(vdir)
        for f in ("slide_plan.json", "final_presentation_cn.pptx", "qa_report.md"):
            assert os.path.exists(os.path.join(vdir, f)), f
        # 工作目录原件不受影响
        assert os.path.exists(os.path.join(deck, "slide_plan.json"))


def test_versions_manifest_appended():
    with tempfile.TemporaryDirectory() as td:
        deck = _make_deck(td)
        sv.save_version(deck, "v1", note="首版")
        sv.save_version(deck, "v2", note="图证修正")
        manifest = os.path.join(deck, "versions", "_versions.md")
        assert os.path.exists(manifest)
        content = Path(manifest).read_text(encoding="utf-8")
        assert "v1" in content and "首版" in content
        assert "v2" in content and "图证修正" in content


def test_nonexistent_deck_dir_returns_error():
    with tempfile.TemporaryDirectory() as td:
        missing = os.path.join(td, "no_such_deck")
        assert sv.save_version(missing, "v1") == 2
        # 不应创建任何目录或清单
        assert not os.path.exists(os.path.join(missing, "versions"))


def test_duplicate_label_errors_unless_force():
    with tempfile.TemporaryDirectory() as td:
        deck = _make_deck(td)
        assert sv.save_version(deck, "v1") == 0
        assert sv.save_version(deck, "v1") == 1  # 重复标签报错
        # 清单不应因报错而重复追加 v1
        manifest = os.path.join(deck, "versions", "_versions.md")
        assert Path(manifest).read_text(encoding="utf-8").count("v1") == 1
        # --force 覆盖
        assert sv.save_version(deck, "v1", force=True) == 0
