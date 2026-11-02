# -*- coding: utf-8 -*-
"""render_formulas.py 测试：xelatex 公式渲染管线（简单/复杂/非法/幂等/manifest）。

风格与 tests/ 现有模块一致：模块级 test_* 函数（run_all.py 按名收集）。
"""
import json
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import render_formulas as rf

import os


def _check_tool_discovery(discover):
    """Exercise the render pipeline with portable, simulated local tools."""
    from PIL import Image

    with patch("shutil.which", side_effect=discover):
        renderer = runpy.run_path(rf.__file__)
    calls = []

    def run_tool(command, **kwargs):
        calls.append(command[0])
        expected = discover(("xelatex", "pdfcrop", "pdftoppm")[len(calls) - 1])
        expected = expected or ("xelatex", "pdfcrop", "pdftoppm")[len(calls) - 1]
        assert command[0] == expected, command[0]
        if len(calls) == 1:
            (Path(kwargs["cwd"]) / "formula.pdf").write_bytes(b"synthetic PDF")
        elif len(calls) == 2:
            Path(command[2]).write_bytes(b"synthetic cropped PDF")
        else:
            Image.new("RGB", (20, 10), "black").save(command[-1] + "-1.png")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    with tempfile.TemporaryDirectory() as directory:
        with patch("subprocess.run", side_effect=run_tool):
            result = renderer["_render_one"]({"id": "portable", "latex": "a+b"}, Path(directory))
        assert "error" not in result, result
        assert result["width_px"] == 20
        assert result["height_px"] == 10
        assert (Path(directory) / "portable.png").is_file()
    assert len(calls) == 3


def test_formula_pipeline_uses_path_commands_without_machine_fallback():
    _check_tool_discovery(lambda name: None)


def test_formula_pipeline_preserves_discovered_tool_paths_with_spaces():
    _check_tool_discovery(lambda name: str(Path(tempfile.gettempdir()) / "local tools" / name))


def _run(entries, outdir=None):
    """写临时 formulas.json 并跑 render_formulas.py 子进程。

    outdir 复用（幂等测试传同一目录）；None 时自动新建。
    """
    td = tempfile.mkdtemp()
    root = Path(td)
    if outdir is None:
        outdir = root / "out"
        outdir.mkdir()
    fjson = root / "formulas.json"
    fjson.write_text(json.dumps(entries), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(Path(rf.__file__)), str(fjson), "--outdir", str(outdir)],
        capture_output=True, text=True, errors="replace", timeout=300)
    return r, outdir


def test_simple_formula_renders_png():
    r, outdir = _run([{"id": "f1", "latex": "t(\\tau) = t_i\\,e^{-\\tau/RC}"}])
    assert r.returncode == 0, r.stderr
    assert (outdir / "f1.png").exists(), "PNG 未生成"
    manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["f1"]["width_px"] > 0
    assert manifest["f1"]["aspect"] > 0


def test_complex_formula_aligned_cases():
    latex = (r"\begin{aligned}"
             r"T_i &= \varepsilon_i x_i + \beta_i \\"
             r"T_{i+1} &= \varepsilon_i x_{(i+1)s} + \beta_i"
             r"\end{aligned}")
    r, outdir = _run([{"id": "f2", "latex": latex, "mode": "display"}])
    assert r.returncode == 0, r.stderr
    assert (outdir / "f2.png").exists(), "aligned 复杂公式渲染失败"


def test_invalid_latex_records_error_not_block():
    r, outdir = _run([{"id": "f3", "latex": "\\frac{"}])  # 未闭合
    assert r.returncode == 0, "失败条目不应阻断整批"
    manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
    assert "error" in manifest["f3"], "非法 LaTeX 应记 error"


def test_invalid_formula_id_records_error_not_write_outside():
    r, outdir = _run([{"id": "../escape", "latex": "a+b"}])
    assert r.returncode == 0
    manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
    assert "error" in manifest["../escape"]
    assert not (outdir.parent / "escape.png").exists()


def test_idempotent_cache_skips_unchanged():
    entries = [{"id": "f4", "latex": "a + b = c"}]
    r1, outdir = _run(entries)
    assert r1.returncode == 0, r1.stderr
    png = outdir / "f4.png"
    mtime1 = png.stat().st_mtime_ns
    r2, _ = _run(entries, outdir=outdir)  # 复用同一 outdir 才有缓存
    assert r2.returncode == 0, r2.stderr
    assert png.stat().st_mtime_ns == mtime1, "缓存命中时不应重渲染"
    assert "缓存跳过" in r2.stdout
    manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["f4"].get("cached"), "缓存条目应标记 cached"


def test_manifest_fields_complete():
    r, outdir = _run([{"id": "f5", "latex": "\\int_0^1 x\\,dx"}])
    assert r.returncode == 0, r.stderr
    manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
    m = manifest["f5"]
    for k in ("file", "width_px", "height_px", "aspect"):
        assert k in m, f"manifest 缺字段 {k}"
    assert m["height_px"] > 0
