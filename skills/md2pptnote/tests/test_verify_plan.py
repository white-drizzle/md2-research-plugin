# -*- coding: utf-8 -*-
"""verify_plan.py 测试：图注一致性校验（source 格式 / bound_to / 图片存在）。"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import verify_plan as v

# fixture 真实存在（tests/fixtures/placeholder.png）
FIXTURE = Path(__file__).parent / "fixtures" / "placeholder.png"


def _tmpdir_with_placeholder():
    """建临时 output 目录（assets/figures/placeholder.png），返回 base_dir。"""
    td = tempfile.mkdtemp()
    fig = Path(td) / "assets" / "figures"
    fig.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE, fig / "placeholder.png")
    return Path(td)


def _plan(slides):
    return {"meta": {}, "slides": slides}


def test_accepts_valid_plan():
    """合法 plan：精确 source、本页 bound_to、图片存在、正文 fig_ref 引用图。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s01", "title": "t",
        "body": [{"type": "ced", "claim": "结论A", "fig_ref": "8"}],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: Fig. 8, [P8]", "bound_to": "s01_ced"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert errs == [], f"合法 plan 不应报错: {errs}"


def test_rejects_orphan_figure():
    """孤儿图：正文没有任何 fig_ref 引用本页图 → 必须拦下。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s01", "title": "t",
        "body": [{"type": "ced", "claim": "结论A"}],   # 无 fig_ref
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: Fig. 8, [P8]", "bound_to": "s01_ced"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert any("fig_ref" in e for e in errs), f"孤儿图应拦下: {errs}"


def test_rejects_fig_ref_source_mismatch():
    """图号漂移：正文 fig_ref 与 source 图号不一致 → 必须拦下。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s01", "title": "t",
        "body": [{"type": "ced", "claim": "结论A", "fig_ref": "7"}],  # source 是 Fig 8
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: Fig. 8, [P8]", "bound_to": "s01_ced"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert any("不一致" in e for e in errs), f"图号不一致应拦下: {errs}"


def test_rejects_fig_ref_without_figure():
    """正文引用了图但本页没有 figure → 必须拦下。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s03", "title": "t",
        "body": [{"type": "point", "lead": "结论", "fig_ref": "2"}],   # 本页无 figure
    }])
    errs, notes = v.verify_plan(p, base)
    assert any("fig_ref" in e for e in errs), f"无图却有 fig_ref 应拦下: {errs}"


def test_rejects_vague_source():
    """模糊 source（'Fig. 吸收率数据'）必须被拦下。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s01", "title": "t",
        "body": [{"type": "ced", "claim": "结论A", "fig_ref": "8"}],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: Fig. 吸收率数据, [P8]", "bound_to": "s01_ced"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert any("source" in e and "格式不规范" in e for e in errs), f"应拦下模糊 source: {errs}"


def test_accepts_panel_bracket_source():
    """带面板括号的 source（'Fig. 10 (a–c)'）应通过。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s09", "title": "t",
        "body": [{"type": "point", "lead": "结论A", "fig_ref": "10"}],
        "figure": {"panels": [{"path": "assets/figures/placeholder.png"}] * 3,
                   "caption": "c", "source": "Source: Fig. 10 (a–c), [P4]",
                   "bound_to": "s09_point1"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert not any("source" in e for e in errs), f"面板括号 source 应通过: {errs}"


def test_accepts_journal_year_source():
    """期刊年份式 source（json_schema 允许 '或期刊年份'）应通过。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s01", "title": "t",
        "body": [{"type": "ced", "claim": "结论A", "fig_ref": "6"}],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: Fig. 6, *Materials*, 2024", "bound_to": "s01_ced"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert not any("source" in e for e in errs), f"期刊年份 source 应通过: {errs}"


def test_rejects_cross_slide_bound_to():
    """bound_to 指向其它页（跨页）必须拦下。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s02", "title": "t",
        "body": [{"type": "ced", "claim": "结论B", "fig_ref": "8"}],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: Fig. 8, [P8]", "bound_to": "s01_point1"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert any("bound_to" in e for e in errs), f"跨页 bound_to 应拦下: {errs}"


def test_rejects_missing_image():
    """figure.path 指向不存在的文件必须拦下。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s01", "title": "t",
        "body": [{"type": "ced", "claim": "结论A", "fig_ref": "8"}],
        "figure": {"path": "assets/figures/no_such_file.jpg", "caption": "c",
                   "source": "Source: Fig. 8, [P8]", "bound_to": "s01_ced"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert any("不存在" in e for e in errs), f"缺图应拦下: {errs}"


def test_rejects_missing_source():
    """figure 缺 source 必须拦下。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s01", "title": "t",
        "body": [{"type": "ced", "claim": "结论A", "fig_ref": "8"}],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c", "bound_to": "s01_ced"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert any("缺 source" in e for e in errs), f"缺 source 应拦下: {errs}"


def test_note_figure_without_figread():
    """有图但无 figread → 软提醒（不阻断），且不产生违规。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s01", "title": "t",
        "body": [{"type": "ced", "claim": "结论A", "fig_ref": "8"}],   # 无 figread
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: Fig. 8, [P8]", "bound_to": "s01_ced"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert errs == [], f"有图无 figread 不应报错: {errs}"
    assert any("figread" in n for n in notes), f"应有 figread 提醒: {notes}"


def test_note_figread_without_figure():
    """有 figread 但无 figure → 软提醒（不阻断），且不产生 fig_ref 违规。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s03", "title": "t",
        "body": [{"type": "figread", "axes": "x", "legend": "l", "shows": "结论"}],  # 无 figure
    }])
    errs, notes = v.verify_plan(p, base)
    assert not any("fig_ref" in e for e in errs), f"有 figread 无图不应报 fig_ref 违规: {errs}"
    assert any("figread" in n for n in notes), f"应有 figread 提醒: {notes}"


def test_no_note_when_figread_present():
    """图 + figread 齐全 → 无违规且无 figread 提醒。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s01", "title": "t",
        "body": [{"type": "ced", "claim": "结论A", "fig_ref": "8"},
                 {"type": "figread", "axes": "x", "legend": "l", "shows": "结论"}],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: Fig. 8, [P8]", "bound_to": "s01_ced"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert errs == [], f"图 + figread 齐全不应报错: {errs}"
    assert not any("figread" in n for n in notes), f"齐全时不应有 figread 提醒: {notes}"


def test_no_notes_for_bare_slide():
    """无图、无 figread、无 fig_ref 的纯文本页 → 零错误零提醒。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s01", "title": "t",
        "body": [{"type": "point", "lead": "结论A"}],
    }])
    errs, notes = v.verify_plan(p, base)
    assert errs == [], f"纯文本页不应报错: {errs}"
    assert notes == [], f"纯文本页不应有提醒: {notes}"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("ALL TESTS PASSED")


def test_external_figure_exempt_from_fig_binding():
    """装饰性外部图（figure.external=True）：无 fig_ref、无 bound_to、非图号 source 均可通过。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s02", "title": "t",
        "body": [{"type": "point", "lead": "结论"}],   # 无 fig_ref
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: IOPscience 期刊官网", "external": True},
    }])
    errs, notes = v.verify_plan(p, base)
    assert errs == [], f"external 图不应被图证绑定检查拦下: {errs}"


def test_external_figure_still_needs_source():
    """external 图缺 source 仍需报错（来源标注不可省）。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s02", "title": "t",
        "body": [{"type": "point", "lead": "结论"}],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "external": True},
    }])
    errs, notes = v.verify_plan(p, base)
    assert any("source" in e for e in errs), f"external 图缺 source 应报错: {errs}"


def test_external_figure_cannot_be_fig_ref():
    """external 装饰图不允许被正文 fig_ref 当作证据引用。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s02", "title": "t",
        "body": [{"type": "ced", "claim": "结论", "fig_ref": "1"}],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: IOPscience 期刊官网", "external": True},
    }])
    errs, notes = v.verify_plan(p, base)
    assert any("装饰图" in e for e in errs), f"external 图被 fig_ref 引用应报错: {errs}"


def test_figread_axes_noaxis_marker_rejected():
    """figread.axes 含"无坐标轴"类残留标记 → 违规（非坐标轴图应省略 axes，内容介绍放 shows）。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s06", "title": "t",
        "body": [
            {"type": "point", "lead": "结论", "fig_ref": "1"},
            {"type": "figread",
             "axes": "示意图（无坐标轴）：加热器布置",
             "legend": "五种布置", "shows": "覆盖典型布置"},
        ],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "bound_to": "s06_point1", "source": "Source: Fig. 1, [P2]"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert any("无坐标轴" in e for e in errs), f"无坐标轴残留标记应报错: {errs}"


def test_figread_axes_clean_passes():
    """figread.axes 为真实坐标轴描述 → 通过（曲线图保留坐标轴行）。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s08", "title": "t",
        "body": [
            {"type": "point", "lead": "结论", "fig_ref": "2"},
            {"type": "figread",
             "axes": "横轴：时间；纵轴：温度",
             "legend": "两曲线", "shows": "升温更快"},
        ],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "bound_to": "s08_point1", "source": "Source: Fig. 2, [P2]"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert errs == [], f"真实坐标轴描述不应报错: {errs}"


def test_accepts_appendix_figure_source():
    """附录图号（'Fig. A.1' + fig_ref 'A.1'）应通过——字母小节号是期刊标准写法。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s16", "title": "t",
        "body": [{"type": "ced", "claim": "结论A", "fig_ref": "A.1"}],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: Fig. A.1, [P12]", "bound_to": "s16_ced"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert errs == [], f"附录图号 source 不应报错: {errs}"


def test_appendix_number_not_confused_with_main_number():
    """附录图号 A.1 与正文图号 1 必须区分——fig_ref '1' 不匹配 source 'Fig. A.1'。"""
    base = _tmpdir_with_placeholder()
    p = _plan([{
        "slide_id": "s16", "title": "t",
        "body": [{"type": "ced", "claim": "结论A", "fig_ref": "1"}],
        "figure": {"path": "assets/figures/placeholder.png", "caption": "c",
                   "source": "Source: Fig. A.1, [P12]", "bound_to": "s16_ced"},
    }])
    errs, notes = v.verify_plan(p, base)
    assert any("不一致" in e for e in errs), f"附录号与正文号混同应拦下: {errs}"


def test_main_figure_number_not_mangled_by_prefix_strip():
    """剥 'Fig.' 前缀后正文章节号仍取数字（防 'g. 1' 被当成附录号 'g1'）。"""
    assert v._norm_fig("Source: Fig. 1 (a,b), [P12]") == "1"
    assert v._norm_fig("Fig. 6h") == "6"
    assert v._norm_fig("A.1") == "a1"
