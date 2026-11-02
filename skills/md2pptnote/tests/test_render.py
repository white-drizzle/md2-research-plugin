# -*- coding: utf-8 -*-
"""render2pptx.py 测试：读 fixture → 渲染 → 重开验证结构。"""
import json, os, sys, tempfile, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import render2pptx as r

FIXTURE = Path(__file__).parent / "fixtures" / "sample_plan.json"
PLACEHOLDER = Path(__file__).parent / "fixtures" / "placeholder.png"

def _render(tmpdir: str) -> str:
    out = os.path.join(tmpdir, "test.pptx")
    fig_dir = os.path.join(tmpdir, "assets", "figures")
    os.makedirs(fig_dir, exist_ok=True)
    shutil.copy(PLACEHOLDER, os.path.join(fig_dir, "placeholder.png"))
    r.main(str(FIXTURE), out, tmpdir)
    return out

def _reopen(path: str):
    from pptx import Presentation
    return Presentation(path)

def test_render_creates_pptx():
    with tempfile.TemporaryDirectory() as td:
        out = _render(td)
        assert os.path.exists(out)
        prs = _reopen(out)
        assert len(prs.slides) == 6

def test_each_slide_has_title_and_note():
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render(td))
        for slide in prs.slides:
            texts = []
            for sh in slide.shapes:
                if sh.has_text_frame and sh.text_frame.text.strip():
                    texts.append(sh.text_frame.text.strip())
            assert any(t for t in texts if "为什么" in t or "[P" in t or "红外焊接是" in t), f"缺少标题: {texts}"
            assert slide.has_notes_slide, "缺少 speaker notes"

def test_figure_slides_embed_picture():
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render(td))
        # s01 和 s02 有 figure，s03 没有
        pic_counts = [sum(1 for sh in sl.shapes if sh.shape_type == 13) for sl in prs.slides]
        assert pic_counts[0] == 1, f"s01 应有 1 张图, got {pic_counts[0]}"
        assert pic_counts[1] == 1, f"s02 应有 1 张图, got {pic_counts[1]}"
        assert pic_counts[2] == 0, f"s03 应无图, got {pic_counts[2]}"
        # s06 是 multi_figure：3 面板 → 3 张图
        assert pic_counts[5] == 3, f"s06 应有 3 张图, got {pic_counts[5]}"

def test_table_and_full_figure_slides():
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render(td))
        # s04 应为 full_table：1 个原生表格（python-pptx 中 TABLE = 19），无图
        s04 = prs.slides[3]
        tbl_count = sum(1 for sh in s04.shapes if sh.has_table)
        pic_count = sum(1 for sh in s04.shapes if sh.shape_type == 13)
        assert tbl_count == 1, f"s04 应有 1 个表格, got {tbl_count}"
        assert pic_count == 0, f"s04 应无图, got {pic_count}"
        # s05 应为 full_figure：1 张图
        s05 = prs.slides[4]
        pic_count = sum(1 for sh in s05.shapes if sh.shape_type == 13)
        assert pic_count == 1, f"s05 应有 1 张图, got {pic_count}"

def test_section_header_layouts_do_not_overlap():
    """带章节标签/两行标题的正文布局不得与正文框重叠。"""
    import verify_pptx
    slides = [
        {
            "slide_id": "s01",
            "section": "01 · 问题与目标",
            "title": "这是一个需要换行的\n问答页标题",
            "body": [{"type": "qa", "question": "听众问题？", "answer": "正文回答。", "takeaway": "核心结论。"}],
            "speaker_note": "测试备注",
            "layout": "question_answer",
        },
        {
            "slide_id": "s02",
            "section": "04 · 结果与工程参数",
            "title": "这是一个需要换行的\n表格页标题",
            "body": [{"type": "point", "lead": "表格结论", "detail": "表格证据", "so_what": "工程含义"}],
            "table": {"headers": ["指标", "结果"], "rows": [["速度", "95.55"]]},
            "speaker_note": "测试备注",
            "layout": "full_table",
        },
        {
            "slide_id": "s03",
            "section": "02 · 温度场与 PCB 响应",
            "title": "这是一个需要换行的\n图文页标题",
            "claim": "图文页结论",
            "body": [{"type": "ced", "claim": "图证结论", "evidence": ["图"], "fig_ref": "1"}],
            "figure": {"path": "assets/figures/placeholder.png", "caption": "测试图", "bound_to": "s03_ced", "interpretation": "测试", "source": "Source: Fig. 1, [P1]"},
            "speaker_note": "测试备注",
            "layout": "claim_figure",
        },
        {
            "slide_id": "s04",
            "section": "02 · 温度场与 PCB 响应",
            "title": "这是一个需要换行的\n整图页标题",
            "figure": {"path": "assets/figures/placeholder.png", "caption": "测试图", "bound_to": "s04_ced", "interpretation": "测试", "source": "Source: Fig. 1, [P1]"},
            "body": [{"type": "ced", "claim": "整图结论", "evidence": ["图"], "fig_ref": "1"}],
            "speaker_note": "测试备注",
            "layout": "full_figure",
        },
        {
            "slide_id": "s05",
            "section": "02 · 温度场与 PCB 响应",
            "title": "这是一个需要换行的\n多面板页标题",
            "figure": {"panels": [{"path": "assets/figures/placeholder.png", "label": "(a)"}, {"path": "assets/figures/placeholder.png", "label": "(b)"}], "caption": "测试图组", "bound_to": "s05_ced", "interpretation": "测试", "source": "Source: Fig. 1, [P1]"},
            "body": [{"type": "ced", "claim": "面板结论", "evidence": ["图"], "fig_ref": "1"}],
            "speaker_note": "测试备注",
            "layout": "multi_figure",
        },
        {
            "slide_id": "s06",
            "section": "02 · 温度场与 PCB 响应",
            "title": "这是一个需要换行的\n无图结论页标题",
            "claim": "无图页结论",
            "body": [{"type": "point", "lead": "正文结论", "detail": "正文证据", "so_what": "正文含义"}],
            "speaker_note": "测试备注",
            "layout": "claim_figure",
        },
    ]
    with tempfile.TemporaryDirectory() as td:
        out = _render_plan(td, slides)
        report = verify_pptx.inspect(out)
        assert report["overlaps"] == 0, report
        assert report["out_of_bounds"] == 0, (report, _all_shapes_in_bounds(_reopen(out)))


def test_shapes_stay_within_canvas():
    """回归：所有形状必须落在画布内（左/上 ≥ 0 且 右/下 ≤ 画布）。"""
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render(td))
        for idx, slide in enumerate(prs.slides):
            for sh in slide.shapes:
                if sh.left is None or sh.top is None or sh.width is None or sh.height is None:
                    continue
                assert sh.left >= 0, f"slide{idx} 形状 left<0: left={sh.left}"
                assert sh.top >= 0, f"slide{idx} 形状 top<0: top={sh.top}"
                assert sh.left + sh.width <= prs.slide_width, \
                    f"slide{idx} 形状右越界: right={sh.left + sh.width}, 画布宽={prs.slide_width}"
                assert sh.top + sh.height <= prs.slide_height, \
                    f"slide{idx} 形状下越界: bottom={sh.top + sh.height}, 画布高={prs.slide_height}"

def _render_plan(tmpdir: str, slides: list) -> str:
    """用给定 slides 渲染一个临时 plan。"""
    plan = {"meta": {"title": "回归", "subtitle": "", "source_papers": ""}, "slides": slides}
    pp = os.path.join(tmpdir, "plan.json")
    with open(pp, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False)
    fig_dir = os.path.join(tmpdir, "assets", "figures")
    os.makedirs(fig_dir, exist_ok=True)
    shutil.copy(PLACEHOLDER, os.path.join(fig_dir, "placeholder.png"))
    out = os.path.join(tmpdir, "test.pptx")
    r.main(pp, out, tmpdir)
    return out

def _all_shapes_in_bounds(prs) -> list:
    """返回越界形状的 (slide_idx, 描述)。"""
    bad = []
    for idx, slide in enumerate(prs.slides):
        for sh in slide.shapes:
            if sh.left is None or sh.top is None or sh.width is None or sh.height is None:
                continue
            if sh.left < 0 or sh.top < 0 \
                    or sh.left + sh.width > prs.slide_width \
                    or sh.top + sh.height > prs.slide_height:
                bad.append((idx, f"x={sh.left} y={sh.top} right={sh.left + sh.width} "
                                  f"bottom={sh.top + sh.height}"))
    return bad

def _estimate_cap_need(sh):
    """按渲染器同一套估算参数，计算该文本框需要的高度（in）。"""
    import math
    w_in = sh.width / 914400.0
    lines = 0
    for para in sh.text_frame.paragraphs:
        t = para.text
        if t:
            lines += max(1, math.ceil(len(t) / max(1.0, w_in * r.CAP_CHARS_PER_IN)))
    return r.CAP_PAD + lines * r.CAP_LINE_H

def test_caption_boxes_hold_their_text():
    """回归：图注文本框高度必须能容纳其内容估算行数（防截断），且不越界。"""
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render(td))
        bad = _all_shapes_in_bounds(prs)
        assert not bad, f"越界: {bad}"
        for idx, slide in enumerate(prs.slides):
            for sh in slide.shapes:
                if not (sh.has_text_frame and sh.text_frame.text.strip()):
                    continue
                if "解读：" not in sh.text_frame.text and "Source:" not in sh.text_frame.text:
                    continue
                need = _estimate_cap_need(sh)
                box_h = sh.height / 914400.0
                assert box_h >= need, \
                    f"slide{idx} 图注框 h={box_h:.2f}in 不足 (估算需 {need:.2f}in): " \
                    f"{sh.text_frame.text[:20]}..."

def test_qa_plus_note_no_overflow():
    """回归：question_answer 带非 qa 元素（note）时不得越界，且 note 在 qa 之后、不压标题。"""
    slides = [{
        "slide_id": "qa_note", "title": "QA + note",
        "body": [
            {"type": "qa", "question": "为什么对称炉腔却温度不均？",
             "answer": "离心风扇扰流破坏对称，后部偏热。", "takeaway": "板位选择要靠 CFD"},
            {"type": "note", "term": "对称炉腔", "explain": "腔体左右镜像对称，但风扇扰流破坏对称"}
        ],
        "speaker_note": "n", "layout": "question_answer",
    }]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        bad = _all_shapes_in_bounds(prs)
        assert not bad, f"question_answer 越界: {bad}"
        # note 文本应在 qa 区域之后（y > 4.8，takeaway 底部），而不是压到标题区。
        # 注意：Q 文本也含"对称炉腔"，必须精确匹配 note 的完整内容（term：explain）
        s = prs.slides[0]
        note_boxes = [sh for sh in s.shapes
                      if sh.has_text_frame
                      and "对称炉腔：腔体左右镜像对称" in sh.text_frame.text]
        assert note_boxes, "未找到 note 文本"
        note_top = note_boxes[0].top / 914400.0
        assert note_top >= 4.6, f"note(y={note_top}) 位置异常（应排在 qa 之后，而非压标题区）"

def test_big_table_no_overflow():
    """回归：行数多（>8）的 full_table + note 不得越界，note 不压表。"""
    slides = [{
        "slide_id": "big_tbl", "title": "大表",
        "body": [{"type": "ced", "claim": "c", "evidence": [], "data": "d"}],
        "table": {
            "headers": ["指标", "A", "B"],
            "rows": [[f"行{i}", "x", "y"] for i in range(10)],
            "col_widths": [2, 3, 3],
            "note": "间距规律：每增加 10 mm，加热速率约减半"
        },
        "speaker_note": "n", "layout": "full_table",
    }]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        bad = _all_shapes_in_bounds(prs)
        assert not bad, f"full_table 越界: {bad}"
        # note 应在表格下方（不压表）
        s = prs.slides[0]
        table_top = table_bottom = note_top = None
        for sh in s.shapes:
            if sh.has_table:
                table_top, table_bottom = sh.top, sh.top + sh.height
            elif sh.has_text_frame and "间距规律" in sh.text_frame.text:
                note_top = sh.top
        assert table_top is not None and table_bottom is not None and note_top is not None, \
            "未找到表格或 note"
        assert note_top >= table_bottom, f"note(y={note_top}) 压在表格(y={table_bottom})上"

def test_full_table_with_figure_mode():
    """图文模式：full_table + figure 时 表在左、图在右、正文在表上方，三者不越界。"""
    slides = [{
        "slide_id": "tbl_fig", "title": "表格配图",
        "body": [
            {"type": "ced", "claim": "结论句", "evidence": ["证据一", "证据二"],
             "data": "关键数据", "fig_ref": "11"},
        ],
        "table": {
            "headers": ["方案", "辐射方式", "适用场景"],
            "rows": [["[P8] LED", "底部穿透", "FPCB"], ["[P9] 灯管", "顶部辐射", "FHE"]],
            "col_widths": [3, 3, 3],
            "note": "两条路线互补"
        },
        "figure": {
            "path": "assets/figures/placeholder.png",
            "caption": "温度曲线对比", "bound_to": "tbl_fig_ced",
            "interpretation": "NIDS 尖峰 vs 对流缓升", "source": "Source: Fig. 11, [P8]"
        },
        "speaker_note": "n", "layout": "full_table",
    }]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        bad = _all_shapes_in_bounds(prs)
        assert not bad, f"full_table 图文模式越界: {bad}"
        s = prs.slides[0]
        table_left = table_right = pic_left = pic_right = None
        for sh in s.shapes:
            if sh.has_table:
                table_left, table_right = sh.left / 914400.0, (sh.left + sh.width) / 914400.0
            elif sh.shape_type == 13:  # 图片
                pic_left, pic_right = sh.left / 914400.0, (sh.left + sh.width) / 914400.0
        assert table_left is not None and pic_left is not None, "表格或图片缺失"
        assert table_right <= pic_left, \
            f"表格右缘({table_right:.2f})应 <= 图左缘({pic_left:.2f})——表格与图应分栏不重叠"
        # fig_ref 渲染出"如图 11 所示"酒红前缀
        body_text = "".join(sh.text_frame.text for sh in s.shapes if sh.has_text_frame)
        assert "如图 11 所示" in body_text, f"应渲染 fig_ref 前缀, got: {body_text}"

def test_readability_guarantees():
    """三大可读性保证：figure.bound_to 非空 / 每页有结论 / 名词有 note 解释。

    直接读 fixture 的 slide_plan.json 断言（不渲染），保护提炼阶段的可读性契约。"""
    with open(FIXTURE, encoding="utf-8") as f:
        plan = json.load(f)
    slides = plan["slides"]
    assert slides, "fixture 不应为空"
    note_seen = False
    for s in slides:
        fig = s.get("figure")
        if fig is not None:
            assert isinstance(fig.get("bound_to"), str) and fig["bound_to"].strip(), \
                f"slide '{s.get('slide_id')}' 有 figure 但 bound_to 为空（图必须指到页内结论）"
        # 每页至少一个"结论"（point.lead / qa.question / ced.claim）
        has_conclusion = False
        for el in s.get("body", []):
            t = el.get("type")
            if (t == "point" and str(el.get("lead", "")).strip()) \
               or (t == "qa" and str(el.get("question", "")).strip()) \
               or (t == "ced" and str(el.get("claim", "")).strip()):
                has_conclusion = True
            if t == "note" and str(el.get("term", "")).strip():
                note_seen = True
        assert has_conclusion, f"slide '{s.get('slide_id')}' 没有任何结论（point.lead/qa.question/ced.claim 至少一个）"
    assert note_seen, "fixture 应有至少一个 note 名词解释（如 FHE）"

def _valid_slide():
    """返回一个合法 slide，测试里再故意破坏某字段。"""
    return {
        "slide_id": "v", "title": "合法页",
        "body": [{"type": "point", "lead": "结论", "detail": "d", "so_what": "s"}],
        "speaker_note": "n", "layout": "point_figure",
    }

def _rejects(slide, what: str):
    """构造单 slide plan 调 _validate_slide，断言抛 ValueError。"""
    plan = {"meta": {}, "slides": [slide]}
    try:
        r._validate_slide(slide)
    except ValueError as e:
        assert what in str(e), f"预期含 '{what}'，实际: {e}"
        return
    raise AssertionError(f"预期抛 ValueError（{what}），但没有抛")

def test_validate_slide_rejects_malformed():
    """校验层关键负路径：坏 body / 缺必填字段 / 超限都应在渲染前被拒。"""
    s = _valid_slide()
    # 合法 slide 不应抛
    r._validate_slide(s)
    s_bad = _valid_slide(); del s_bad["slide_id"]
    _rejects(s_bad, "slide_id")
    s_bad = _valid_slide(); del s_bad["layout"]
    _rejects(s_bad, "layout")
    # 各负路径
    s_bad = _valid_slide(); s_bad["body"] = [{"type": "point", "detail": "无 lead"}]
    _rejects(s_bad, "lead")
    s_bad = _valid_slide(); s_bad["body"] = ["hello"]           # 非 dict 元素
    _rejects(s_bad, "body 元素必须是对象")
    s_bad = _valid_slide(); s_bad["body"] = [{"type": "qa", "answer": "a"}]  # qa 缺 question
    _rejects(s_bad, "question")
    s_bad = _valid_slide(); s_bad["body"] = [{"type": "note", "explain": "e"}]  # note 缺 term
    _rejects(s_bad, "term")
    s_bad = _valid_slide(); s_bad["body"] = [{"type": "ced", "evidence": ["e"]}]  # ced 缺 claim
    _rejects(s_bad, "claim")
    s_bad = _valid_slide(); s_bad["body"] = [{"type": "piont", "lead": "拼写错误"}]
    _rejects(s_bad, "未知")
    s_bad = _valid_slide(); s_bad["speaker_note"] = ""
    _rejects(s_bad, "speaker_note")
    s_bad = _valid_slide(); s_bad["layout"] = "full_table"
    _rejects(s_bad, "必须包含 table")
    s_bad = _valid_slide(); s_bad["layout"] = "full_figure"
    _rejects(s_bad, "必须包含 figure")
    s_bad = _valid_slide(); s_bad["body"] = [{"type": "formula", "width_in": 2, "height_in": 1}]
    _rejects(s_bad, "path")
    s_bad = _valid_slide(); s_bad["table"] = {"headers": ["a", "b"], "rows": [["only one"]]}
    _rejects(s_bad, "矩形")
    s_bad = _valid_slide(); s_bad["table"] = {"headers": ["a", "b"], "rows": [["a", "b"]], "col_widths": [1]}
    _rejects(s_bad, "col_widths")
    s_bad = _valid_slide(); s_bad["body"] = [{"type": "point", "lead": "x"}]
    s_bad["figure"] = {"path": "a.png", "caption": "c", "interpretation": "i"}   # 缺 bound_to
    _rejects(s_bad, "bound_to")
    s_bad = _valid_slide(); s_bad["body"] = [{"type": "point", "lead": "x"}]
    s_bad["figure"] = {"caption": "c", "bound_to": "x", "interpretation": "i"}   # 缺 path
    _rejects(s_bad, "path")
    s_bad = _valid_slide(); s_bad["table"] = {"headers": ["a"], "rows": [[str(i)] for i in range(11)]}   # 11 行
    s_bad["layout"] = "full_table"
    _rejects(s_bad, "上限 10")
    s_bad = _valid_slide(); s_bad["table"] = {"headers": ["a"], "rows": [[str(i)] for i in range(16)]}   # 16 行
    s_bad["layout"] = "full_table"
    _rejects(s_bad, "上限 10")
    s_bad = _valid_slide(); s_bad["body"] = [
        {"type": "qa", "question": "q1", "answer": "a"},
        {"type": "qa", "question": "q2", "answer": "b"},                         # 双 qa
    ]
    s_bad["layout"] = "question_answer"
    _rejects(s_bad, "最多 1 个")
    # multi_figure 面板校验
    s_bad = _valid_slide()
    s_bad["layout"] = "multi_figure"
    s_bad["figure"] = {"caption": "c", "bound_to": "x", "interpretation": "i"}   # multi_figure 缺 panels
    _rejects(s_bad, "panels")
    s_bad = _valid_slide()
    s_bad["layout"] = "multi_figure"
    s_bad["figure"] = {"panels": [], "caption": "c", "bound_to": "x", "interpretation": "i"}  # panels 空
    _rejects(s_bad, "非空列表")
    s_bad = _valid_slide()
    s_bad["layout"] = "multi_figure"
    s_bad["figure"] = {"panels": [{"path": "a.png"}] * 10, "caption": "c",      # 10 面板超限
                       "bound_to": "x", "interpretation": "i"}
    _rejects(s_bad, "上限 9")
    s_bad = _valid_slide()
    s_bad["layout"] = "multi_figure"
    s_bad["figure"] = {"panels": [{"label": "(a)"}], "caption": "c",            # 面板缺 path
                       "bound_to": "x", "interpretation": "i"}
    _rejects(s_bad, "panels[0]")

def _multi_slide(n_panels: int, label_some: bool = True) -> dict:
    """构造 n 面板 multi_figure slide，全部面板用 placeholder.png。"""
    panels = [{"path": "placeholder.png", "label": f"({chr(97 + i)})"} for i in range(n_panels)]
    return {
        "slide_id": f"mf{n_panels}", "title": f"多面板 {n_panels}",
        "body": [{"type": "ced", "claim": "c", "evidence": [], "data": "d"}],
        "figure": {
            "panels": panels,
            "caption": f"统一图注 {n_panels} 面板",
            "subcaptions": "; ".join(f"({chr(97+i)}) 子图{i+1}" for i in range(n_panels)),
            "bound_to": f"mf{n_panels}_ced",
            "interpretation": "i",
            "source": "Source: Fig. X, [P9]"
        },
        "speaker_note": "n", "layout": "multi_figure",
    }

def test_multi_figure_panel_counts():
    """multi_figure：2/4/6 面板 → 恰好渲染对应数量的图片，且不越界。"""
    for n in (2, 4, 6):
        with tempfile.TemporaryDirectory() as td:
            prs = _reopen(_render_plan(td, [_multi_slide(n)]))
            s = prs.slides[0]
            pic_count = sum(1 for sh in s.shapes if sh.shape_type == 13)
            assert pic_count == n, f"{n} 面板应有 {n} 张图, got {pic_count}"
            bad = _all_shapes_in_bounds(prs)
            assert not bad, f"{n} 面板越界: {bad}"

def test_multi_figure_auto_labels():
    """multi_figure：无 label 的面板自动按顺序生成 (a)(b)(c)… 角标文本。"""
    slides = [_multi_slide(3)]
    slides[0]["figure"]["panels"] = [{"path": "placeholder.png"} for _ in range(3)]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        s = prs.slides[0]
        texts = [sh.text_frame.text for sh in s.shapes
                 if sh.has_text_frame and sh.text_frame.text.strip()]
        for label in ("(a)", "(b)", "(c)"):
            assert any(label in t for t in texts), f"缺少角标 {label}: {texts}"

def test_multi_figure_validation_gate():
    """multi_figure 校验负路径由 _validate_slide 拒绝（panels 必填/上限/panel.path）。"""
    s = _multi_slide(2)
    r._validate_slide(s)   # 合法
    # 缺 panels 且缺顶层 path → multi_figure 必填 panels
    s_bad = _multi_slide(2)
    del s_bad["figure"]["panels"]
    try:
        r._validate_slide(s_bad)
        raise AssertionError("预期抛 ValueError（multi_figure 缺 panels），没有抛")
    except ValueError as e:
        assert "panels" in str(e)

def test_multi_figure_body_modes():
    """multi_figure 三种模式：
    - 有 body + 面板≥3（短正文）→ 顶部正文条 + 全宽栅格（图主导，grid 从 2.75 起）
    - 有 body + 面板<3 → 左文右图（正文左 + 图右单列）
    - 无 body → 全宽栅格
    均不得越界，图片数=面板数。"""
    # 短正文 + 3 面板：grid_top 应从 2.75 起（> GRID_TOP 1.45），图片在正文条下方
    slides = [_multi_slide(3)]
    slides[0]["body"] = [
        {"type": "point", "lead": "A", "detail": "B", "so_what": "C"},
        {"type": "point", "lead": "D", "detail": "E", "so_what": "F"},
    ]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        s = prs.slides[0]
        pics = [sh for sh in s.shapes if sh.shape_type == 13]
        assert len(pics) == 3, f"短正文3面板应有 3 图, got {len(pics)}"
        # 图在正文条下方：y >= 2.75
        for p in pics:
            assert p.top / 914400.0 >= 2.7, f"短正文模式图未下移到正文条下方: y={p.top/914400.0:.2f}"
        bad = _all_shapes_in_bounds(prs)
        assert not bad, f"短正文3面板越界: {bad}"
    # 有 body + 2 面板：左文右图，正文在左（x<8.5），图在右（x>=8.5）
    slides = [_multi_slide(2)]
    slides[0]["body"] = [{"type": "ced", "claim": "c", "evidence": ["e"], "data": "d"}]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        s = prs.slides[0]
        pics = [sh for sh in s.shapes if sh.shape_type == 13]
        assert len(pics) == 2
        for p in pics:
            assert p.left / 914400.0 >= 8.4, f"左文右图模式图应在右侧栏: x={p.left/914400.0:.2f}"
        # 正文文本存在（含 ced claim）
        texts = [sh.text_frame.text for sh in s.shapes if sh.has_text_frame]
        assert any("c" in t for t in texts), "左文右图模式缺少正文"
        bad = _all_shapes_in_bounds(prs)
        assert not bad, f"左文右图2面板越界: {bad}"

def test_three_landscape_panels_side_by_side():
    """回归：全宽模式 3 个横图面板应并排一行（3 列），而非 2+1 排列——避免 (a)(b) 之间
    露大空白浪费空间。三张图 top 相同（同一行）、互不越界。"""
    slides = [_multi_slide(3)]   # placeholder.png 是 400x300 横图
    slides[0]["body"] = [
        {"type": "point", "lead": "A", "detail": "B", "so_what": "C"},
        {"type": "point", "lead": "D", "detail": "E", "so_what": "F"},
    ]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        s = prs.slides[0]
        pics = [sh for sh in s.shapes if sh.shape_type == 13]
        assert len(pics) == 3, f"3 面板应有 3 图, got {len(pics)}"
        tops = [p.top / 914400.0 for p in pics]
        assert max(tops) - min(tops) < 0.05, f"3 横图应并排一行(同 top), 实际 top={tops}"
        # 统一缩放 → 同高（顶/底对齐），避免横图高度参差
        heights = [p.height / 914400.0 for p in pics]
        assert max(heights) - min(heights) < 0.05, f"3 横图应同高对齐, 实际高={heights}"
        # 横向从左到右排开，互不重叠
        lefts = sorted(p.left / 914400.0 for p in pics)
        widths = [p.width / 914400.0 for p in pics]
        for i in range(len(lefts) - 1):
            assert lefts[i] + widths[i] < lefts[i + 1], f"子图重叠: {lefts}"
        bad = _all_shapes_in_bounds(prs)
        assert not bad, f"3 横图并排越界: {bad}"

def test_layout_contract_figure_renders_caption():
    """布局契约：任何带 figure 的 slide 必须渲染出图注（含 caption 或 interpretation）。
    防"布局改了但忘记渲染图注"这类静默丢元素（本次 multi_figure 丢 body 的同型问题）。"""
    slides = [_multi_slide(2)]
    slides[0]["body"] = [{"type": "ced", "claim": "c", "evidence": [], "data": "d"}]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        s = prs.slides[0]
        texts = [sh.text_frame.text for sh in s.shapes if sh.has_text_frame]
        joined = "\n".join(texts)
        assert "解读：" in joined, "multi_figure 图注必须含解读"
        assert "Source:" in joined, "multi_figure 图注必须含 Source"


def test_panel_labels_do_not_overlap_pictures():
    """回归：面板角标 (a)(b) 必须放在子图正上方（图内不出现角标白底框），
    不得叠在图上遮挡内容。角标框底在图顶上方（留空隙），与图零重叠。"""
    slides = [_multi_slide(2)]
    slides[0]["body"] = [{"type": "ced", "claim": "c", "evidence": [], "data": "d"}]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        s = prs.slides[0]
        pics = [sh for sh in s.shapes if sh.shape_type == 13]
        assert len(pics) == 2, f"2 面板应有 2 图, got {len(pics)}"
        labels = [sh for sh in s.shapes if sh.has_text_frame
                  and sh.text_frame.text.strip() in ("(a)", "(b)")]
        assert len(labels) == 2, f"应有 2 个角标, got {len(labels)}"
        for lb in labels:
            lb_bottom = lb.top + lb.height
            # 角标框底必须在某张图顶上方（同列），且在图顶上方的条带内（留 LABEL_GAP 空隙）
            matched = any(
                abs(lb.left - p.left) / 914400.0 < 0.1
                and lb_bottom < p.top
                and (p.top - lb_bottom) / 914400.0 <= 0.25
                for p in pics
            )
            assert matched, (
                f"角标 {lb.text_frame.text} 未在图正上方: 底={lb_bottom/914400.0:.3f}in, "
                f"图顶={[p.top/914400.0 for p in pics]}"
            )
        # 角标框本身不越界
        bad = _all_shapes_in_bounds(prs)
        assert not bad, f"角标外移后越界: {bad}"


def test_fig_ref_renders_prefix():
    """fig_ref：带 fig_ref 的结论元素渲染"如图 xx 所示，"前缀（酒红与图注 source 呼应），无 fig_ref 不加。"""
    slides = [{
        "slide_id": "fr", "title": "fig_ref",
        "body": [
            {"type": "ced", "claim": "MET 结合强度最优", "fig_ref": "6",
             "evidence": ["e"], "data": "d"},
            {"type": "point", "lead": "无需图证的结论"},
            {"type": "ced", "claim": "IMC 线性反比", "fig_ref": "10 (a–c)",
             "evidence": [], "data": "d"},
        ],
        "figure": {"panels": [{"path": "placeholder.png"}] * 3,
                   "caption": "c", "subcaptions": "(a);(b);(c)",
                   "bound_to": "fr_ced1", "interpretation": "i",
                   "source": "Source: Fig. 6, [P9]"},
        "speaker_note": "n", "layout": "multi_figure",
    }]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        s = prs.slides[0]
        texts = [sh.text_frame.text for sh in s.shapes if sh.has_text_frame]
        joined = "\n".join(texts)
        # fig_ref="6" 的 claim → 前缀（fig_ref 主图号 6 与 source 图号 6 一致，正文渲染不含校验）
        assert "如图 6 所示，MET 结合强度最优" in joined, f"fig_ref 前缀缺失: {joined}"
        # fig_ref="10 (a–c)" 的 claim → 前缀带括号图号
        assert "如图 10 (a–c) 所示，IMC 线性反比" in joined, f"面板图号前缀缺失: {joined}"
        # 无 fig_ref 的元素不加前缀：单独成行且不以"如图"开头
        plain = [t for t in texts if "无需图证的结论" in t][0]
        plain_lines = [ln for ln in plain.splitlines() if "无需图证的结论" in ln]
        assert plain_lines, f"未找到 point 段: {plain}"
        assert not plain_lines[0].startswith("如图"), \
            f"无 fig_ref 不应加前缀: {plain_lines[0]}"


def test_qa_fig_ref_renders_prefix():
    """question_answer：qa 带 fig_ref 时渲染酒红"如图 N 所示，"前缀拼接在 Q 行前（与 point/ced 图证绑定一致）。"""
    slides = [{
        "slide_id": "qa_fr", "title": "QA 带图证",
        "body": [
            {"type": "qa", "question": "为什么红外焊接热分布不均？",
             "answer": "炉腔气流被夹具遮挡，底部与边缘升温速率差异显著。",
             "takeaway": "板位选择需考虑气流遮挡", "fig_ref": "15"},
        ],
        "figure": {"path": "placeholder.png",
                   "caption": "c", "bound_to": "qa_fr_qa1",
                   "interpretation": "i",
                   "source": "Source: Fig. 15, [P1]"},
        "speaker_note": "n", "layout": "question_answer",
    }]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        s = prs.slides[0]
        texts = _slide_texts(s)
        joined = "\n".join(texts)
        # 前缀与问题在同一段落内拼接：Q 行以"如图 15 所示，"开头
        assert "如图 15 所示，Q: 为什么红外焊接热分布不均？" in joined, \
            f"qa fig_ref 前缀缺失: {joined}"
        # 不得出现缺前缀的裸 Q 行（Q 行必须紧跟"如图 N 所示，"）
        bare_q = [ln for t in texts for ln in t.splitlines()
                  if ln.strip().startswith("Q:")]
        assert not bare_q, f"存在缺前缀的裸 Q 行: {bare_q}"
        # 图注 source 呼应图号
        assert "Source: Fig. 15, [P1]" in joined, f"图注 source 缺失: {joined}"
        # 图文分栏不越界
        bad = _all_shapes_in_bounds(prs)
        assert not bad, f"question_answer 越界: {bad}"


def test_figread_renders_reading_guide():
    """figread：渲染 坐标轴/图例/图意 三行灰色说明（无"读图"标签——AI 感强已移除），紧跟结论元素。"""
    slides = [{
        "slide_id": "fr2", "title": "figread",
        "body": [
            {"type": "point", "lead": "吸收差异显著", "fig_ref": "7",
             "detail": "d", "so_what": "s"},
            {"type": "figread",
             "axes": "横轴波长，纵轴吸收率",
             "legend": "红=铜覆 PET，灰=裸 PET",
             "shows": "850nm 处铜覆 PET 吸 32%"},
        ],
        "figure": {"path": "placeholder.png",
                   "caption": "c", "bound_to": "fr2_point1",
                   "interpretation": "i",
                   "source": "Source: Fig. 7, [P1]"},
        "speaker_note": "n", "layout": "point_figure",
    }]
    with tempfile.TemporaryDirectory() as td:
        prs = _reopen(_render_plan(td, slides))
        s = prs.slides[0]
        joined = "\n".join(sh.text_frame.text for sh in s.shapes if sh.has_text_frame)
        # 三行说明都在（figread 紧跟"如图 7 所示"结论之后）
        assert "坐标轴：横轴波长，纵轴吸收率" in joined, f"axes 缺失: {joined}"
        assert "图例：红=铜覆 PET，灰=裸 PET" in joined, f"legend 缺失: {joined}"
        assert "图意：850nm 处铜覆 PET 吸 32%" in joined, f"shows 缺失: {joined}"
        # 无"读图"标签（该词 AI 感强，正文不再出现）
        assert "读图" not in joined, f"不应出现'读图'标签: {joined}"
        # 顺序：结论"如图 7 所示"在"坐标轴"之前
        assert joined.index("如图 7 所示") < joined.index("坐标轴"), \
            f"说明应紧跟结论之后: {joined}"


def _slide_texts(slide) -> list:
    return [sh.text_frame.text for sh in slide.shapes
            if sh.has_text_frame and sh.text_frame.text.strip()]

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("ALL TESTS PASSED")


def test_cover_layout_renders_centered_title():
    """cover layout：渲染 title/subtitle/claim/footer，无图无重叠。"""
    plan = {
        "meta": {},
        "slides": [{
            "slide_id": "s01", "title": "测试封面标题",
            "subtitle": "English subtitle",
            "claim": "主题句",
            "body": [{"type": "note", "term": "用途", "explain": "测试"}],
            "footer": "期刊信息 2025",
            "speaker_note": "测试封面。",
            "layout": "cover",
        }]
    }
    with tempfile.TemporaryDirectory() as td:
        plan_path = os.path.join(td, "plan.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False)
        out = os.path.join(td, "t.pptx")
        r.main(plan_path, out, td)
        prs = _reopen(out)
        texts = [sh.text_frame.text for sh in prs.slides[0].shapes if sh.has_text_frame]
        joined = "\n".join(texts)
        assert "测试封面标题" in joined, f"封面标题缺失: {joined}"
        assert "English subtitle" in joined, f"英文副题缺失: {joined}"
        assert "期刊信息 2025" in joined, f"footer 缺失: {joined}"


def test_toc_layout_renders_sections():
    """toc layout：渲染每个 point lead 章节行。"""
    plan = {
        "meta": {},
        "slides": [{
            "slide_id": "s03", "title": "目录",
            "body": [
                {"type": "point", "lead": "01 · 背景", "detail": "动机"},
                {"type": "point", "lead": "02 · 方法", "detail": "做法"},
            ],
            "speaker_note": "测试目录。",
            "layout": "toc",
        }]
    }
    with tempfile.TemporaryDirectory() as td:
        plan_path = os.path.join(td, "plan.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False)
        out = os.path.join(td, "t.pptx")
        r.main(plan_path, out, td)
        prs = _reopen(out)
        texts = [sh.text_frame.text for sh in prs.slides[0].shapes if sh.has_text_frame]
        joined = "\n".join(texts)
        assert "01 · 背景" in joined, f"目录行缺失: {joined}"
        assert "02 · 方法" in joined, f"目录行缺失: {joined}"
