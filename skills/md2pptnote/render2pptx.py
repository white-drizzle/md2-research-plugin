#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染器：slide_plan.json → PPTX。纯渲染，不判断内容。

从 build_ppt.py 演进：保留排版辅助函数，新增 JSON 驱动层 + layout 渲染。
"""
import json, os, math
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# ── 配色（Nature 学术风，同 build_ppt.py）──
INK = RGBColor(0x1A, 0x1A, 0x1A)
GRAY = RGBColor(0x5A, 0x5A, 0x5A)
ACCENT = RGBColor(0x8B, 0x3A, 0x3A)   # 深酒红
LIGHT_GRAY = RGBColor(0x99, 0x99, 0x99)
BG = RGBColor(0xFD, 0xFC, 0xFA)

W = Inches(13.333)
H = Inches(7.5)

# 图注文本排版参数（11/11.5/9pt 中文，行高按 0.24in 估，顶底 padding 0.16in）
CAP_CHARS_PER_IN = 5.5     # 中文约 5.5 字/in（11pt，保守值：真实字体按 6+ 字/in 更窄）
CAP_LINE_H = 0.24          # 每行高（in）
CAP_PAD = 0.16             # 顶底 padding（in）
CAP_H_MAX = 1.6            # 图注框最大高度上限（in）
CAP_MARGIN = 0.25          # 图注框外额外边距（in）——给估算误差留安全余量

# multi_figure 栅格参数（16:9 画布，13.333 × 7.5 in）
GRID_PAD = 0.12            # 面板之间间隙（in）
GRID_TOP = 1.45            # 栅格起始 y（title 下方）
GRID_MAX_BOTTOM = 7.28     # 栅格底 + 底部图注之间的上界（in）
LABEL_SIZE = 11            # 面板角标 (a)(b) 字号（pt）
LABEL_BAND = 0.32          # 子图正上方的角标条带高度（in）——角标放图上方，不遮挡图片
LABEL_GAP = 0.08           # 角标框底与图顶的空隙（in）——角标悬浮在图上方，不压顶边

# ══════════════ 排版辅助函数（复制自 build_ppt.py，保持原样）══════════════

def add_bg(slide, color=BG):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color

def add_text(slide, x, y, w, h, runs, size=18, color=INK, bold=False,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space_after=6,
             line_spacing=1.12):
    """runs: str 或 [(text, dict)] 列表（每段）。段元素也可为 [(text, dict), …] 列表——
    同一段内多个 run 拼接（如"如图 6h 所示，"酒红前缀 + 正文）。"""
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    if isinstance(runs, str):
        # \n 拆成独立段落（LibreOffice 对同段落内 <a:br/> 换行的首行渲染为左对齐，
        # 段落级换行才可靠居中——P10 封面标题首行偏左即此因）
        runs = [(line, {}) for line in runs.split("\n")]
    for i, para in enumerate(runs):
        if isinstance(para, list):
            segs = para
            over = segs[-1][1]   # 段级排版参数取最后一段（主文本）
        else:
            segs = [para]
            over = para[1]
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = over.get("align", align)
        p.space_after = Pt(over.get("space_after", space_after))
        p.line_spacing = over.get("line_spacing", line_spacing)
        for txt, o in segs:
            run = p.add_run()
            # 剥离 markdown 强调标记（`*斜体*` / `**粗体**`），PPT 里直接显示原文
            run.text = str(txt).replace("**", "").replace("*", "")
            f = run.font
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.color.rgb = o.get("color", color)
            f.name = "Microsoft YaHei"
    return box

def add_title(slide, text, sub=None, accent=ACCENT):
    add_text(slide, Inches(0.6), Inches(0.28), Inches(12.1), Inches(0.7),
             text, size=28, bold=True, color=INK)
    if sub:
        add_text(slide, Inches(0.62), Inches(0.9), Inches(12), Inches(0.4),
                 sub, size=13, color=GRAY)

def add_section_tag(slide, tag, x=Inches(0.6), y=Inches(0.28)):
    add_text(slide, x, y, Inches(6.2), Inches(0.36), tag, size=13,
             color=ACCENT, bold=True)


def add_content_header(slide, s):
    """统一正文页眉：章节标签单行显示，标题在其下方；封面/目录由专用布局自行处理。"""
    has_section = bool(s.get("section"))
    if has_section:
        add_section_tag(slide, s["section"])
        title_y = Inches(0.72)
    else:
        title_y = Inches(0.28)
    title_lines = max(1, s["title"].count("\n") + 1)
    base_title_h = 0.9 if has_section else 0.7
    title_h = Inches(max(base_title_h, 0.35 + title_lines * 0.38))
    add_text(slide, Inches(0.6), title_y, Inches(12.1), title_h,
             s["title"], size=26, bold=True, color=INK)
    return title_y.inches + title_h.inches

def add_bullets(slide, x, y, w, h, items, size=16, gap=8, color=INK):
    """items: 列表，每项是 (前缀, 正文) 或 str。前缀如 '▸ ' 或 '① '。"""
    runs = []
    for it in items:
        if isinstance(it, tuple):
            txt, over = it
            over = over or {}
            runs.append((txt, {"size": over.get("size", size),
                               "color": over.get("color", color),
                               "space_after": over.get("space_after", gap)}))
        else:
            runs.append((it, {"size": size, "color": color, "space_after": gap}))
    add_text(slide, x, y, w, h, runs, size=size)

def add_caption(slide, text, y=Inches(7.02), size=10.5, color=GRAY):
    add_text(slide, Inches(0.6), y, Inches(12.1), Inches(0.36), text,
             size=size, color=color)

def _est_lines_h(text: str, w_in: float, size_pt: float = 11) -> float:
    """估算一段文字需要的高度（in）：按行数×行高，clamp 到 [0.8, CAP_H_MAX]。

    与 _cap_h_for 共用同一套估算参数（中文按 CAP_CHARS_PER_IN 字/in）。"""
    chars = len(str(text))
    lines = max(1, math.ceil(chars / max(1.0, w_in * CAP_CHARS_PER_IN)))
    return max(0.8, min(CAP_H_MAX, CAP_PAD + lines * CAP_LINE_H))

def _grid_span(n: int) -> tuple[int, int]:
    """multi_figure 栅格列数、行数。

    规则（对齐 md2htmlnote 的 figure-row 2 列原则，末行单面板整行居中）：
    - 1/2 面板 → 单列（每张较大）
    - 3–6 面板 → 2 列（3=2×2-1 末行居中, 4=2×2, 5=2×2+1 居中, 6=2×3）
    - ≥7 面板 → 3 列（行数更多，每格仍可读）
    行数 = ceil(n/列)。"""
    if n <= 2:
        cols = 1
    elif n <= 6:
        cols = 2
    else:
        cols = 3
    rows = math.ceil(n / cols)
    return cols, rows


def _panel_is_landscape(fig_dir: str, panel: dict) -> bool:
    """面板图片是否横图（宽>高）。文件缺失/损坏时按 False 处理（回退 2 列）。"""
    path = _resolve_fig_path(fig_dir, panel.get("path", ""))
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
            return w > h
    except Exception:
        return False

def _cap_h_for(caption, interpretation, source, w_in):
    """估算图注框需要的高度（in）：按内容行数×行高 + padding，clamp 到 [0.8, CAP_H_MAX]。

    一行放不下的内容折成多行（中文按 CAP_CHARS_PER_IN 字/in 估算）。
    w_in 是图注框宽度（in）。"""
    lines = 0
    for txt in (caption, ("解读：" + interpretation) if interpretation else None, source):
        if not txt:
            continue
        chars = len(str(txt))
        lines += max(1, math.ceil(chars / max(1.0, w_in * CAP_CHARS_PER_IN)))
    return max(0.8, min(CAP_H_MAX, CAP_PAD + lines * CAP_LINE_H))

def _missing_fig(slide, path, x, y, w):
    """图片缺失/损坏时的占位提示（SKILL.md：不静默丢弃）。"""
    add_text(slide, x, y, w, Inches(1), f"[缺失图片] {os.path.basename(path)}",
             size=12, color=RGBColor(0xC0, 0x00, 0x00))

def add_fig(slide, path, x, y, w, h=None, max_h=None, caption=None, source=None, interpretation=None):
    """按比例放入图片；w 给定，h 自动等比（若 h 未给）。max_h 限制最大高度（超出则反向缩 w 保比例）。

    图注框高度按内容自适应：先按内容估出 cap_h，据此反向限制图片高度
    （图片底 ≤ 7.5 - cap_h - 边距），图注框再占满图片底部到画布底的剩余空间，
    两者合起来永不越界、文字不被截断。"""
    if not os.path.exists(path):
        _missing_fig(slide, path, x, y, w)
        return
    try:
        from PIL import Image
        im = Image.open(path)
        iw, ih = im.size
    except Exception:
        # 文件存在但损坏（UnidentifiedImageError / OSError 等）：占位提示，不崩溃
        _missing_fig(slide, path, x, y, w)
        return
    if h is None:
        h = Emu(int(w * ih / iw))
    # 图注框高度：按内容估算（in），并据此反推图片最大高
    w_in = w / 914400.0
    y_in = y / 914400.0
    cap_h = _cap_h_for(caption, interpretation, source, w_in)
    cap_reserve = cap_h + 0.05 + CAP_MARGIN            # 图注 + 间隙 + 边距（in）
    img_max_h = max(Inches(0.5), Inches(7.5 - y_in - cap_reserve))
    if max_h is not None:
        img_max_h = min(img_max_h, max_h)
    if h > img_max_h:
        # 等比缩到 img_max_h：新宽度 = w * (img_max_h / h)
        w = Emu(int(w * img_max_h / h))
        h = img_max_h
    pic = slide.shapes.add_picture(path, x, y, width=w, height=h)
    cap_runs = []
    if caption:
        cap_runs.append((caption, {"size": 11, "color": GRAY, "space_after": 2}))
    if interpretation:
        cap_runs.append(("解读：" + interpretation, {"size": 11.5, "color": ACCENT, "space_after": 2}))
    if source:
        cap_runs.append((source, {"size": 9, "color": RGBColor(0x99, 0x99, 0x99), "space_after": 0}))
    if cap_runs:
        cap_y = y + h + Inches(0.05)
        add_text(slide, x, cap_y, w, Inches(7.5) - cap_y, cap_runs, size=11)
    return pic

def add_panel_label(slide, pic_top, pic_left, label, size=LABEL_SIZE):
    """面板角标 (a)/(b)…：白底灰字小框，放在子图正上方的条带（LABEL_BAND）内，
    不叠在图上——避免遮挡图片内容。pic_top/pic_left 是子图左上角坐标。
    框底与图顶留 LABEL_GAP 空隙，角标悬浮在图上方。"""
    if not label:
        return
    box = slide.shapes.add_textbox(pic_left, Inches(pic_top / 914400.0 - LABEL_BAND),
                                   Inches(0.6), Inches(LABEL_BAND - LABEL_GAP))
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    tf = box.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.BOTTOM
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = label
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x5A, 0x5A, 0x5A)
    run.font.name = "Microsoft YaHei"

def add_table(slide, x, y, w, rows_data, col_widths=None, header=True,
              font_size=12.5, row_h=0.38):
    """rows_data: list of list。第一行作表头。"""
    n_r, n_c = len(rows_data), len(rows_data[0])
    shape = slide.shapes.add_table(n_r, n_c, x, y, w, Inches(row_h * n_r))
    tbl = shape.table
    if col_widths:
        total = sum(col_widths)
        for ci, cw in enumerate(col_widths):
            tbl.columns[ci].width = Emu(int(w * cw / total))
    for ri, row in enumerate(rows_data):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.margin_top = Pt(2)
            cell.margin_bottom = Pt(2)
            cell.margin_left = Pt(4)
            cell.margin_right = Pt(4)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = str(val)
            run.font.size = Pt(font_size)
            run.font.name = "Microsoft YaHei"
            if (header and ri == 0) or (str(val).startswith("**")):
                run.font.bold = True
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if (header and ri == 0) else INK
            else:
                run.font.color.rgb = INK
            if header and ri == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = ACCENT
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if ri % 2 == 1 else RGBColor(0xF5, 0xF2, 0xEB)
    return tbl

def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text

# ══════════════ body 元素渲染（论证链）══════════════

def _render_body_points(slide, x, y, w, body, size=16, h=None, align=PP_ALIGN.LEFT, fig_dir=None):
    """把 body 数组渲染成论证链。point/ced → 三段式；qa → 问答式；note → 灰色小字。h 覆盖文本框高（默认 5.0in）。

    带 fig_ref 的元素：结论句前面加酒红前缀"如图 xx 所示，"（与图注 source 同色，视觉锚点）。
    align 供封面等居中布局复用。
    formula 元素（type="formula"，path 指向 EMF/SVG 转换产物）：正文流中插入公式图片——
    先把已累积文本落盘为文本框，在下方插入图片，后续元素继续排（如"核心公式"独立成行）。
    """
    def _lead(lead, el):
        """结论句段：带 fig_ref 时 = 酒红前缀 + 正文（同段两个 run 拼接）。"""
        ref = el.get("fig_ref")
        if not ref:
            return [(lead, {"size": size, "color": INK, "bold": True, "space_after": 2})]
        return [
            (f"如图 {ref} 所示，", {"size": size, "color": ACCENT, "bold": True, "space_after": 0}),
            (lead, {"size": size, "color": INK, "bold": True, "space_after": 2}),
        ]

    def _est_h(runs, w_in, size):
        """粗略估算已累积文本高度（英寸），用于公式插图前推进 y。

        保守系数：中文字符按 0.23in 宽、行高按字号的 1.25 倍 + 段距——
        宁可估算偏高留白，不可偏低导致文本溢出与公式图/后续元素重叠。
        w_in 可能是 Emu 整数值（Inches(4.2) = 3810240），先换算为英寸。"""
        import math
        w_emu = float(w_in)
        w_inc = w_emu / 914400.0 if w_emu > 1000 else w_emu
        lines = 0
        for para in runs:
            text = "".join(s[0] for s in para) if isinstance(para, list) else para[0]
            cpl = max(6, int(w_inc / 0.23))
            lines += max(1, math.ceil(len(text) / cpl))
        return lines * (size / 72) * 1.25 + len(runs) * 0.08

    runs = []
    has_formula = any(el.get("type") == "formula" for el in body)
    # 无 formula 的页保持旧行为（单文本框、固定高度），避免估算高度回归
    if not has_formula:
        for el in body:
            t = el["type"]
            if t == "point":
                runs.append(_lead(el["lead"], el))
                if el.get("detail"):
                    runs.append((el["detail"], {"size": size - 1, "color": GRAY, "space_after": 2}))
                if el.get("so_what"):
                    runs.append(("→ " + el["so_what"], {"size": size - 1, "color": ACCENT, "bold": True, "space_after": 8}))
            elif t == "qa":
                ref = el.get("fig_ref")
                if ref:
                    runs.append([
                        (f"▸ 如图 {ref} 所示，",
                         {"size": size, "color": ACCENT, "bold": True, "space_after": 0}),
                        (el["question"], {"size": size, "color": INK, "bold": True, "space_after": 2}),
                    ])
                else:
                    runs.append([("▸ " + el["question"],
                                  {"size": size, "color": INK, "bold": True, "space_after": 2})])
                if el.get("answer"):
                    runs.append((el["answer"], {"size": size - 1, "color": GRAY, "space_after": 2}))
                if el.get("takeaway"):
                    runs.append(("→ " + el["takeaway"], {"size": size - 1, "color": ACCENT, "bold": True, "space_after": 8}))
            elif t == "ced":
                runs.append(_lead(el["claim"], el))
                for e in el.get("evidence", []):
                    runs.append(("· " + e, {"size": size - 1, "color": GRAY, "space_after": 2}))
                if el.get("data"):
                    runs.append((el["data"], {"size": size - 1, "color": ACCENT, "bold": True, "space_after": 8}))
            elif t == "note":
                runs.append((f"{el.get('term', '')}：{el.get('explain', '')}",
                             {"size": size - 2, "color": GRAY, "space_after": 6}))
            elif t == "figread":
                for key, label in (("axes", "坐标轴"), ("legend", "图例"), ("shows", "图意")):
                    v = el.get(key)
                    if v:
                        runs.append((f"{label}：{v}",
                                     {"size": size - 2, "color": GRAY, "space_after": 2}))
        add_text(slide, x, y, w, Inches(5.0) if h is None else h, runs, size=size, align=align)
        return

    # cur_y 内部统一用英寸 float（Emu + 英寸 float 会污染单位，被 python-pptx 截断为 EMU 整数）
    cur_y = y.inches if hasattr(y, "inches") else float(y)

    def _flush():
        nonlocal runs, cur_y
        if not runs:
            return
        est_h = _est_h(runs, w, size)
        add_text(slide, x, Inches(cur_y), w, Inches(max(est_h, 0.35)), runs, size=size, align=align)
        cur_y += est_h + 0.08
        runs = []

    for el in body:
        t = el["type"]
        if t == "formula":
            # 正文公式：先落盘已累积文本，再插入公式图片（EMF/SVG 转换产物），继续后续元素
            _flush()
            width_in = float(el.get("width_in", 5.0))
            height_in = float(el.get("height_in", 1.4))
            if not fig_dir:
                raise ValueError("formula 插入缺少 fig_dir")
            path = _resolve_fig_path(fig_dir, el.get("path", ""))
            if not path or not os.path.isfile(path):
                raise ValueError(f"formula 图片不存在: {el.get('path', '')}")
            x_in = x.inches if hasattr(x, "inches") else float(x) / 914400.0
            if x_in + 0.15 + width_in > 13.333 or cur_y + height_in > 7.5:
                raise ValueError(f"formula 尺寸超出画布: x={x_in:.2f}, y={cur_y:.2f}, w={width_in:.2f}, h={height_in:.2f}")
            slide.shapes.add_picture(str(path), x + Inches(0.15), Inches(cur_y),
                                     Inches(width_in), Inches(height_in))
            cur_y += height_in + 0.14
        elif t == "point":
            runs.append(_lead(el["lead"], el))
            if el.get("detail"):
                runs.append((el["detail"], {"size": size - 1, "color": GRAY, "space_after": 2}))
            if el.get("so_what"):
                runs.append(("→ " + el["so_what"], {"size": size - 1, "color": ACCENT, "bold": True, "space_after": 8}))
        elif t == "qa":
            ref = el.get("fig_ref")
            if ref:
                # "▸ 如图 x 所示，" 酒红 + 问题正文深色，同段两 run 拼接
                runs.append([
                    (f"▸ 如图 {ref} 所示，",
                     {"size": size, "color": ACCENT, "bold": True, "space_after": 0}),
                    (el["question"], {"size": size, "color": INK, "bold": True, "space_after": 2}),
                ])
            else:
                runs.append([("▸ " + el["question"],
                              {"size": size, "color": INK, "bold": True, "space_after": 2})])
            if el.get("answer"):
                runs.append((el["answer"], {"size": size - 1, "color": GRAY, "space_after": 2}))
            if el.get("takeaway"):
                runs.append(("→ " + el["takeaway"], {"size": size - 1, "color": ACCENT, "bold": True, "space_after": 8}))
        elif t == "ced":
            runs.append(_lead(el["claim"], el))
            for e in el.get("evidence", []):
                runs.append(("· " + e, {"size": size - 1, "color": GRAY, "space_after": 2}))
            if el.get("data"):
                runs.append((el["data"], {"size": size - 1, "color": ACCENT, "bold": True, "space_after": 8}))
        elif t == "note":
            runs.append((f"{el.get('term', '')}：{el.get('explain', '')}",
                         {"size": size - 2, "color": GRAY, "space_after": 6}))
        elif t == "figread":
            # 读图指引：坐标轴/图例/图意（有值才渲染），紧跟在"如图 N 所示"结论后。
            # 不渲染"读图"标签——该词 AI 感强；非坐标轴图（示意图/照片）只留图例+图意，
            # 坐标轴行由数据侧省略（verify_plan 会拦截"无坐标轴"残留标记）。
            for key, label in (("axes", "坐标轴"), ("legend", "图例"), ("shows", "图意")):
                v = el.get(key)
                if v:
                    runs.append((f"{label}：{v}",
                                 {"size": size - 2, "color": GRAY, "space_after": 2}))
    _flush()

# ══════════════ layout 渲染函数 ══════════════

def render_point_figure(slide, s, ctx):
    """非对称左文右图：文本 60-70% + 图窄 30-40%。"""
    fig_dir = ctx["fig_dir"]
    header_bottom = add_content_header(slide, s)
    fig = s.get("figure")
    body_top = max(1.7, header_bottom + 0.15)
    fig_top = max(1.5, header_bottom + 0.3)
    if fig:
        # 有 figure（无论文件是否存在）：保留右栏，add_fig 在文件缺失/损坏时画占位框
        body_w = Inches(7.3)
        fig_x = Inches(8.3)
        fig_w = Inches(4.9)
    else:
        body_w = Inches(12.1)
        fig_x = None
        fig_w = None
    _render_body_points(slide, Inches(0.6), Inches(body_top), body_w, s["body"], size=16, fig_dir=ctx["fig_dir"])
    if fig_x is not None:
        _add_figure(slide, fig_dir, fig, fig_x, Inches(fig_top), fig_w, max_h=Inches(4.8))

def render_claim_figure(slide, s, ctx):
    """图主导（页 60%+）+ 右侧窄解读带（claim + 证据）。"""
    fig_dir = ctx["fig_dir"]
    header_bottom = add_content_header(slide, s)
    claim_y = max(1.3, header_bottom + 0.15)
    add_text(slide, Inches(0.6), Inches(claim_y), Inches(7.6), Inches(0.5),
             s.get("claim", ""), size=16, bold=True, color=INK)
    fig = s.get("figure")
    content_top = max(1.7, header_bottom + 0.05)
    figure_top = max(2.1, header_bottom + 0.45)
    if fig:
        # 图主导：左图（缺失/损坏时 add_fig 画占位框）+ 右窄解读带
        _add_figure(slide, fig_dir, fig, Inches(0.6), Inches(figure_top), Inches(7.6), max_h=Inches(4.2))
        _render_body_points(slide, Inches(8.6), Inches(content_top), Inches(4.2), s["body"], size=14, fig_dir=ctx["fig_dir"])
    else:
        body_top = max(content_top, claim_y + 0.65)
        _render_body_points(slide, Inches(0.6), Inches(body_top), Inches(12.1), s["body"], size=16,
                            h=Inches(7.5 - body_top))

def render_question_answer(slide, s, ctx):
    """问答式：大字号 question + answer + 底部 takeaway 酒红条。
    有 figure → 仿 point_figure 左文右图（文本 60% + 图窄 40%）。"""
    fig_dir = ctx["fig_dir"]
    header_bottom = add_content_header(slide, s)
    qa_els = [el for el in s["body"] if el["type"] == "qa"]
    other_els = [el for el in s["body"] if el["type"] != "qa"]
    fig = s.get("figure")
    if fig:
        # 有图：文本占左 60%，图右栏窄 40%（对齐 point_figure 的图文分栏）
        body_w = Inches(7.3)
        fig_x = Inches(8.3)
        fig_w = Inches(4.9)
    else:
        body_w = Inches(12.1)
        fig_x = None
    y = max(1.6, header_bottom + 0.15)
    if qa_els:
        qa = qa_els[0]
        # qa 带 fig_ref 时加酒红前缀"如图 N 所示，"（与 point/ced 一致，衔接图证绑定）
        # 注意：多 run 必须用嵌套列表 [[(txt, dict), ...]]——同一段内拼两个 run；
        # 扁平列表会被 add_text 当成多个段落，前缀会掉到 Q 行的上一行。
        if qa.get("fig_ref"):
            add_text(slide, Inches(0.6), Inches(y), body_w, Inches(0.7), [
                [(f"如图 {qa['fig_ref']} 所示，",
                  {"size": 22, "color": ACCENT, "bold": True, "space_after": 0}),
                 ("Q: " + qa["question"],
                  {"size": 22, "color": INK, "bold": True, "space_after": 2})],
            ])
        else:
            add_text(slide, Inches(0.6), Inches(y), body_w, Inches(0.7),
                     "Q: " + qa["question"], size=22, bold=True, color=INK)
        add_text(slide, Inches(0.6), Inches(y + 0.85), body_w, Inches(1.1),
                 qa.get("answer", ""), size=17, color=GRAY)
        if qa.get("takeaway"):
            add_text(slide, Inches(0.6), Inches(y + 2.1), body_w, Inches(0.5),
                     "→ " + qa["takeaway"], size=16, bold=True, color=ACCENT)
        y += 2.8
    if other_els:
        # qa 占满画布时，其余元素（note/figread 等）紧凑排在 qa 之后，且文本框不越界（画布 7.5in）。
        # 注意 y 是 float，必须用 Inches() 包起来再 min，否则得到裸 float 会被当成 5 EMU≈0。
        oy = min(Inches(y + 0.3), Inches(6.2))
        _render_body_points(slide, Inches(0.6), oy, body_w, other_els, size=15,
                            h=Inches(7.5) - oy, fig_dir=ctx["fig_dir"])
    if fig_x is not None:
        _add_figure(slide, fig_dir, fig, fig_x, Inches(1.9 if s.get("section") else 1.5), fig_w, max_h=Inches(4.4))

def render_full_table(slide, s, ctx):
    """表格页。默认全宽表格 + 表下强调文字。
    有 figure → 表格左 60% + 图右栏窄 40%（仿 point_figure），正文论证链紧凑排在表上方。"""
    fig_dir = ctx["fig_dir"]
    header_bottom = add_content_header(slide, s)
    tbl = s.get("table")
    if not tbl:
        return
    fig = s.get("figure")
    if fig:
        # ── 图文模式：正文条 + 左表 + 右图 ──
        body_w = Inches(7.8)
        # 正文论证链（如有）紧凑排在表上方
        y_body = max(1.3, header_bottom + 0.15)
        body_h = 1.95
        if s.get("body"):
            _render_body_points(slide, Inches(0.6), Inches(y_body), body_w, s["body"],
                                size=12.5, h=Inches(body_h), fig_dir=ctx["fig_dir"])
        table_y = y_body + body_h + 0.2
        rows = [tbl["headers"]] + tbl["rows"]
        n_r = len(rows)
        note = tbl.get("note")
        table_reserve = 0.95 if note else 0.2
        max_table_h = max(0.0, 7.5 - table_y - table_reserve)
        row_h = max(0.22, min(0.5, max_table_h / n_r))
        table_font = 11 if row_h < 0.28 else 12
        add_table(slide, Inches(0.6), Inches(table_y), body_w, rows,
                  col_widths=tbl.get("col_widths"), font_size=table_font, row_h=row_h)
        if note:
            note_y = max(5.6, table_y + row_h * n_r + 0.15)
            add_text(slide, Inches(0.6), Inches(note_y), body_w,
                     Inches(7.5) - Inches(note_y), note, size=12, color=ACCENT, bold=True)
        _add_figure(slide, fig_dir, fig, Inches(8.7), Inches(max(1.5, header_bottom + 0.3)), Inches(4.0), max_h=Inches(4.6))
        return
    rows = [tbl["headers"]] + tbl["rows"]
    n_r = len(rows)
    note = tbl.get("note")
    # ── 无图模式：正文论证链（如有）排在表上方，表下强调文字 ──
    y_body = max(1.3, header_bottom + 0.15)
    body_h = 0.0
    if s.get("body"):
        body_h = 1.7
        _render_body_points(slide, Inches(0.6), Inches(y_body), Inches(12.1), s["body"],
                            size=14, h=Inches(body_h), fig_dir=ctx["fig_dir"])
    table_y = y_body + body_h + 0.2
    # 行多时压缩行高：表 + note（如有）都留在画布内（画布 7.5in）
    if note:
        max_table_h = max(0.0, 7.5 - table_y - 0.95)
    else:
        max_table_h = max(0.0, 7.5 - table_y - 0.2)
    row_h = max(0.22, min(0.5, max_table_h / n_r))
    table_font = 11 if row_h < 0.28 else 13
    table_bottom = table_y + row_h * n_r
    add_table(slide, Inches(0.6), Inches(table_y), Inches(12.1), rows,
              col_widths=tbl.get("col_widths"), font_size=table_font, row_h=row_h)
    if note:
        # note 常规在 5.4；表底超过 5.4 时移到表下方（不压表、不越界）
        note_y = max(5.4, table_bottom + 0.15)
        add_text(slide, Inches(0.6), Inches(note_y), Inches(12.1),
                 Inches(7.5) - Inches(note_y), note, size=13, color=ACCENT, bold=True)

def render_full_figure(slide, s, ctx):
    fig_dir = ctx["fig_dir"]
    header_bottom = add_content_header(slide, s)
    fig = s.get("figure")
    body_top = max(1.7, header_bottom + 0.15)
    if s.get("body"):
        _render_body_points(slide, Inches(0.6), Inches(body_top), Inches(12.1), s["body"],
                            size=13, h=Inches(1.25), fig_dir=ctx["fig_dir"])
    if fig:
        figure_top = max(1.2, header_bottom + 0.3)
        if s.get("body"):
            figure_top = max(3.1, body_top + 1.45)
        _add_figure(slide, fig_dir, fig, Inches(1.5), Inches(figure_top), Inches(10.3), max_h=Inches(4.0))

def render_multi_figure(slide, s, ctx):
    """多面板图栅格。两种模式：
    - 有 body（正文论证链）→ 左文右图：正文左 60% + 面板栅格右 40%（单列排），图注在栅格下方
    - 无 body → 全宽栅格 + 底部统一图注
    单元格内图片等比铺满、不裁切，末行单面板整行居中。"""
    fig_dir = ctx["fig_dir"]
    header_bottom = add_content_header(slide, s)
    fig = s.get("figure")
    figure_top = max(1.2, header_bottom + 0.3)
    if not fig or not fig.get("panels"):
        # 无 panels 时退化为单图（保持向后兼容：旧 plan 只有 path）
        _add_figure(slide, fig_dir, fig or {}, Inches(1.5), Inches(figure_top),
                    Inches(10.3), max_h=Inches(4.5))
        return
    panels = fig["panels"]
    n = len(panels)
    body = s.get("body") or []
    # 短正文 + 多面板（≥3）→ 顶部全宽正文条 + 全宽图栅格（图主导，图大清晰）
    short_body = len(body) <= 2
    if body and short_body and n >= 3:
        body_top = max(1.05, header_bottom + 0.15)
        _render_body_points(slide, Inches(0.6), Inches(body_top), Inches(12.1), body,
                            size=13, h=Inches(1.5), fig_dir=ctx["fig_dir"])
        grid_top = body_top + 1.65
    elif body:
        # ── 左文右图模式 ──
        grid_top = max(1.5, header_bottom + 0.3)
        body_w = Inches(7.6)
        body_top = max(1.6, header_bottom + 0.35)
        _render_body_points(slide, Inches(0.6), Inches(body_top), body_w, body, size=15, fig_dir=ctx["fig_dir"])
        # 右栏图栅格：x 从 8.5 到 12.7（宽 4.2in）。面板 ≤2 单列；≥3 用 2 列（每格更宽，避免单列堆叠过小）
        grid_x = 8.5
        grid_w_in = 13.333 - grid_x - 0.6   # 4.23 in
        if n >= 3:
            cols = 2
        else:
            cols = 1
        rows = math.ceil(n / cols)
        cell_gap = GRID_PAD
        cell_w_in = (grid_w_in - cell_gap * (cols - 1)) / cols
        # 图注（窄，caption/subcaptions/interpretation/source）
        cap_w_in = grid_w_in
        cap_lines = 0
        for txt in (fig.get("caption"), fig.get("subcaptions"), fig.get("interpretation"), fig.get("source")):
            if txt:
                cap_lines += max(1, math.ceil(len(str(txt)) / max(1.0, cap_w_in * CAP_CHARS_PER_IN)))
        cap_h_in = max(0.8, min(CAP_H_MAX, CAP_PAD + cap_lines * CAP_LINE_H))
        grid_bottom_in = 7.5 - cap_h_in - 0.1
        grid_h = grid_bottom_in - grid_top
        cell_h_in = (grid_h - cell_gap * (rows - 1)) / rows
        from PIL import Image as _PIL
        for idx, panel in enumerate(panels):
            path = _resolve_fig_path(fig_dir, panel.get("path", ""))
            # 末行单面板：整行居中
            last_alone = (idx == n - 1) and (idx % cols == 0)
            cell_w_act = cell_w_in
            col_off = (grid_w_in - cell_w_in) / 2 if last_alone else (idx % cols) * (cell_w_in + cell_gap)
            cell_y = Inches(grid_top + (idx // cols) * (cell_h_in + cell_gap))
            if not os.path.exists(path):
                _missing_fig(slide, path, Inches(grid_x + col_off), cell_y, Inches(cell_w_act))
                continue
            try:
                im = _PIL.open(path)
                iw, ih = im.size
            except Exception:
                _missing_fig(slide, path, Inches(grid_x + col_off), cell_y, Inches(cell_w_act))
                continue
            # 每格顶部预留角标条带（图正上方），图片在条带下方、垂直居中于剩余区域
            cell_h_avail = cell_h_in - LABEL_BAND
            scale = min(cell_w_act / iw, cell_h_avail / ih)
            pw = max(Inches(0.1), Emu(int(iw * scale * 914400)))
            ph = max(Inches(0.1), Emu(int(ih * scale * 914400)))
            px = Inches(grid_x + col_off + (cell_w_act - pw / 914400.0) / 2)
            py = Inches(grid_top + (idx // cols) * (cell_h_in + cell_gap) + LABEL_BAND
                        + (cell_h_avail - ph / 914400.0) / 2)
            slide.shapes.add_picture(path, px, py, width=pw, height=ph)
            label = panel.get("label") or (f"({chr(97 + idx)})" if idx < 26 else f"({idx + 1})")
            add_panel_label(slide, py, px, label)
        # 右栏图注
        cap_runs = []
        if fig.get("caption"):
            cap_runs.append((fig["caption"], {"size": 10.5, "color": GRAY, "space_after": 2}))
        if fig.get("subcaptions"):
            cap_runs.append((fig["subcaptions"], {"size": 9.5, "color": RGBColor(0x5A, 0x5A, 0x5A), "space_after": 2}))
        if fig.get("interpretation"):
            cap_runs.append(("解读：" + fig["interpretation"], {"size": 10.5, "color": ACCENT, "space_after": 2}))
        if fig.get("source"):
            cap_runs.append((fig["source"], {"size": 9, "color": RGBColor(0x99, 0x99, 0x99), "space_after": 0}))
        if cap_runs:
            cap_y = Inches(grid_bottom_in + 0.05)
            add_text(slide, Inches(grid_x), cap_y, Inches(cap_w_in),
                     Inches(7.5) - cap_y, cap_runs, size=10.5)
        return
    else:
        grid_top = GRID_TOP
    # ── 无 body（或短正文）：全宽栅格模式（grid_top 决定起始 y）──
    # 3 面板且全是横图（w>h）时并排一行（3 列），避免 2+1 排列里 (a)(b) 之间露大空白
    # 而浪费空间；其余面板数照旧走 _grid_span。
    if n == 3 and all(_panel_is_landscape(fig_dir, p) for p in panels):
        cols, rows = 3, 1
    else:
        cols, rows = _grid_span(n)
    # 栅格区域：左右边距 0.6，全宽 13.333 - 1.2 = 12.133 in
    grid_w_in = 13.333 - 1.2
    # 统一图注框（底部预留）：内容 = caption + 子注 + interpretation + source
    cap_w_in = 13.333 - 1.2
    cap_lines = 0
    for txt in (fig.get("caption"), fig.get("subcaptions"), fig.get("interpretation"), fig.get("source")):
        if txt:
            cap_lines += max(1, math.ceil(len(str(txt)) / max(1.0, cap_w_in * CAP_CHARS_PER_IN)))
    cap_h_in = max(0.8, min(CAP_H_MAX, CAP_PAD + cap_lines * CAP_LINE_H))
    grid_bottom_in = 7.5 - cap_h_in - 0.15
    # 可用高度下限保护：图注太长时强制网格≥1 行高，宁可图注密一点
    if grid_bottom_in - grid_top < 1.0:
        grid_bottom_in = grid_top + 1.0
    grid_h = grid_bottom_in - grid_top
    cell_gap = GRID_PAD
    cell_w_in = (grid_w_in - cell_gap * (cols - 1)) / cols
    cell_h_in = (grid_h - cell_gap * (rows - 1)) / rows
    from PIL import Image as _PIL
    # 整行并排（如 3 横图一行）时统一渲染高度：每张图同高、顶/底对齐，宽度按各自比例。
    # 避免"每格独立等比缩放"导致横图高度参差（(a) 比 (b)(c) 高出一截）。
    # 注意统一的是高度而非 scale——统一 scale 会按最"矮"的图过度缩小其他图。
    row_uniform = rows == 1 and cols == n
    for idx, panel in enumerate(panels):
        path = _resolve_fig_path(fig_dir, panel.get("path", ""))
        # 末行单面板（如 5 面板 2 列 → 2×2 + 第 5 张）：与其他格同宽，整行水平居中
        # （不占整行，保持 3 行 2 列的规整节奏，第 5 张落在第 3、4 张之间下方）。
        last_alone = (idx == n - 1) and (idx % cols == 0)
        cell_w_act = Inches(cell_w_in)
        col_off = (grid_w_in - cell_w_in) / 2 if last_alone else \
            (idx % cols) * (cell_w_in + cell_gap)
        cell_x = Inches(0.6 + col_off)
        cell_y = Inches(grid_top + (idx // cols) * (cell_h_in + cell_gap))
        if not os.path.exists(path):
            _missing_fig(slide, path, cell_x, cell_y, cell_w_act)
            continue
        try:
            im = _PIL.open(path)
            iw, ih = im.size
        except Exception:
            _missing_fig(slide, path, cell_x, cell_y, cell_w_act)
            continue
        # 单元格内等比缩放，居中（不裁切），短边贴边；顶部预留角标条带
        w_in_act = cell_w_act / 914400.0
        cell_h_avail = cell_h_in - LABEL_BAND
        if row_uniform:
            # 整行并排：每格占满格宽、各自自然高度（宽高比不同→高度各异是几何必然），
            # 垂直居中于行（见下方 py）——比贴顶更视觉平衡
            scale = min(w_in_act / iw, cell_h_avail / ih)
            pw = max(Inches(0.1), Emu(int(iw * scale * 914400)))
            ph = max(Inches(0.1), Emu(int(ih * scale * 914400)))
        else:
            scale = min(w_in_act / iw, cell_h_avail / ih)
            pw = max(Inches(0.1), Emu(int(iw * scale * 914400)))
            ph = max(Inches(0.1), Emu(int(ih * scale * 914400)))
        px = cell_x + Emu(int((w_in_act - pw / 914400.0) * 914400 / 2))
        if row_uniform:
            # 整行并排：每格占满格宽（利用率高），垂直居中于行——3 张横图并排
            # 高度各异是几何必然（宽高比不同），垂直居中比贴顶更视觉平衡
            py = Inches(grid_top + LABEL_BAND + (cell_h_avail - ph / 914400.0) / 2)
        else:
            py = Inches(grid_top + (idx // cols) * (cell_h_in + cell_gap) + LABEL_BAND
                        + (cell_h_avail - ph / 914400.0) / 2)
        slide.shapes.add_picture(path, px, py, width=pw, height=ph)
        label = panel.get("label") or (f"({chr(97 + idx)})" if idx < 26 else f"({idx + 1})")
        add_panel_label(slide, py, px, label)
    # 底部统一图注
    cap_runs = []
    if fig.get("caption"):
        cap_runs.append((fig["caption"], {"size": 11, "color": GRAY, "space_after": 2}))
    if fig.get("subcaptions"):
        cap_runs.append((fig["subcaptions"], {"size": 10, "color": RGBColor(0x5A, 0x5A, 0x5A), "space_after": 2}))
    if fig.get("interpretation"):
        cap_runs.append(("解读：" + fig["interpretation"], {"size": 11.5, "color": ACCENT, "space_after": 2}))
    if fig.get("source"):
        cap_runs.append((fig["source"], {"size": 9, "color": RGBColor(0x99, 0x99, 0x99), "space_after": 0}))
    if cap_runs:
        cap_y = Inches(grid_bottom_in + 0.05)
        add_text(slide, Inches(0.6), cap_y, Inches(cap_w_in),
                 Inches(7.5) - cap_y, cap_runs, size=11)

# ══════════════ 图渲染共用 ══════════════

def _resolve_fig_path(fig_dir, path):
    """把 plan 里的图片路径解析成 fig_dir 内的安全路径。"""
    root = Path(fig_dir).resolve()
    raw = str(path or "")
    if "assets/figures" in raw:
        sub = raw.split("assets/figures/", 1)[1]
    else:
        sub = Path(raw).name
    candidate = (root / sub).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"图片路径越出 assets/figures: {path}") from exc
    return str(candidate)

def _add_figure(slide, fig_dir, fig, x, y, w, max_h=None):
    # 兼容 panels 退化：非 multi_figure 布局下 figure 可能只给了 panels（json_schema
    # 允许"有 panels 时可省略 path"）——此时取第一个面板作为单图渲染。
    path = fig.get("path") or ((fig.get("panels") or [{}])[0].get("path") or "")
    path = _resolve_fig_path(fig_dir, path)
    # external 装饰图（如期刊封面）不渲染"解读"行——装饰图无需解读，规则化防复发
    interpretation = None if fig.get("external") else fig.get("interpretation")
    add_fig(slide, path, x, y, w, max_h=max_h,
            caption=fig.get("caption"),
            source=fig.get("source"),
            interpretation=interpretation)

def render_cover(slide, s, ctx):
    """封面：居中大标题（34pt，可含 \\n 手动换行）+ 英文副题（灰）+ 主题句（酒红）+ body 居中列 + 底部 footer 来源行。"""
    cx = Inches(1.67)   # 居中列：宽 10in（13.333 - 2×1.67）
    title = s.get("title", "")
    title_h = max(1.3, 0.55 * (title.count("\n") + 1) + 0.15)
    add_text(slide, cx, Inches(1.85), Inches(10.0), Inches(title_h),
             title, size=34, bold=True, color=INK, align=PP_ALIGN.CENTER)
    y = 1.85 + title_h + 0.1
    if s.get("subtitle"):
        add_text(slide, cx, Inches(y), Inches(10.0), Inches(0.55),
                 s["subtitle"], size=16, color=GRAY, align=PP_ALIGN.CENTER)
        y += 0.6
    if s.get("claim"):
        add_text(slide, cx, Inches(y), Inches(10.0), Inches(0.7),
                 s["claim"], size=18, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
        y += 0.85
    if s.get("body"):
        _render_body_points(slide, cx, Inches(y), Inches(10.0), s["body"], size=14,
                            h=Inches(7.5) - Inches(y) - Inches(0.9), align=PP_ALIGN.CENTER,
                            fig_dir=ctx["fig_dir"])
    if s.get("footer"):
        add_text(slide, cx, Inches(6.9), Inches(10.0), Inches(0.4),
                 s["footer"], size=11, color=LIGHT_GRAY, align=PP_ALIGN.CENTER)

def render_toc(slide, s, ctx):
    """目录：编号章节大行列表（lead 20pt bold + detail 灰注），垂直均匀分布。"""
    add_text(slide, Inches(0.6), Inches(0.28), Inches(12.1), Inches(0.7),
             s.get("title", ""), size=26, bold=True, color=INK)
    els = [el for el in s.get("body", []) if el["type"] == "point"]
    if not els:
        return
    top, bottom = 1.7, 6.9
    gap = (bottom - top) / len(els)
    for i, el in enumerate(els):
        runs = [(el.get("lead", ""), {"size": 20, "color": INK, "bold": True, "space_after": 2})]
        if el.get("detail"):
            runs.append((el["detail"], {"size": 14, "color": GRAY, "space_after": 0}))
        add_text(slide, Inches(1.2), Inches(top + i * gap), Inches(11.0),
                 Inches(gap - 0.15), runs)

LAYOUTS = {
    "point_figure": render_point_figure,
    "claim_figure": render_claim_figure,
    "question_answer": render_question_answer,
    "full_table": render_full_table,
    "full_figure": render_full_figure,
    "multi_figure": render_multi_figure,
    "cover": render_cover,
    "toc": render_toc,
}

def _validate_slide(s):
    """渲染前 schema 校验：把 KeyError 变成边界处明确报错。失败抛 ValueError。"""
    sid = s.get("slide_id")
    if not isinstance(sid, str) or not sid.strip():
        raise ValueError("slide 缺少 slide_id（slide_id 为必填非空字符串）")
    if not isinstance(s.get("title"), str) or not s["title"].strip():
        raise ValueError(f"slide '{sid}' 缺少 title（title 为必填且非空）")
    if s["title"].count("\n") + 1 > 2:
        raise ValueError(f"slide '{sid}' 的 title 最多允许手动拆成两行")
    section = s.get("section")
    if section is not None:
        if not isinstance(section, str) or not section.strip():
            raise ValueError(f"slide '{sid}' 的 section 必须是非空字符串")
        if "\n" in section or len(section) > 32:
            raise ValueError(f"slide '{sid}' 的 section 必须是一行短标签（最多32字符）")
    if not isinstance(s.get("body"), list) or not s["body"]:
        raise ValueError(f"slide '{sid}' 缺少 body（body 为必填且非空列表）")
    if not isinstance(s.get("speaker_note"), str) or not s["speaker_note"].strip():
        raise ValueError(f"slide '{sid}' 缺少 speaker_note（正式汇报页必须有一句话备注）")
    layout = s.get("layout")
    if layout not in LAYOUTS:
        raise ValueError(f"slide '{sid}' 的 layout '{layout}' 未知或缺失，可选: {', '.join(LAYOUTS)}")

    if layout == "full_table" and not isinstance(s.get("table"), dict):
        raise ValueError(f"slide '{sid}' 的 full_table 必须包含 table")
    if layout == "full_figure" and not isinstance(s.get("figure"), dict):
        raise ValueError(f"slide '{sid}' 的 full_figure 必须包含 figure")

    def _need(el, field, label=None):
        v = el.get(field)
        if not (isinstance(v, str) and v.strip()):
            name = label or el.get("type", "?")
            raise ValueError(f"slide '{sid}' 的 {name} 缺少 {field}（{field} 为必填且非空）")

    # body 元素必填字段（按类型）
    allowed_body_types = {"point", "qa", "note", "ced", "figread", "formula"}
    for el in s["body"]:
        if not isinstance(el, dict):
            raise ValueError(f"slide '{sid}' 的 body 元素必须是对象，got {type(el).__name__}")
        t = el.get("type")
        if t not in allowed_body_types:
            raise ValueError(f"slide '{sid}' 的 body type '{t}' 未知，可选: {', '.join(sorted(allowed_body_types))}")
        if t == "point":
            _need(el, "lead")
        elif t == "qa":
            _need(el, "question")
        elif t == "note":
            _need(el, "term")
        elif t == "ced":
            _need(el, "claim")
        elif t == "formula":
            _need(el, "path")
            raw_path = el["path"].replace("\\", "/")
            if ".." in Path(raw_path).parts:
                raise ValueError(f"slide '{sid}' 的 formula path 不得越出 assets/figures")
            for dimension in ("width_in", "height_in"):
                value = el.get(dimension)
                if not isinstance(value, (int, float)) or not math.isfinite(value) or not (0 < value <= 12):
                    raise ValueError(f"slide '{sid}' 的 formula {dimension} 必须是 0~12 的有限正数")

    # figure / table 必填字段
    fig = s.get("figure")
    if fig is not None:
        if not isinstance(fig, dict):
            raise ValueError(f"slide '{sid}' 的 figure 必须是对象")
        panels = fig.get("panels")
        if panels is not None:
            if not isinstance(panels, list) or not panels:
                raise ValueError(f"slide '{sid}' 的 figure.panels 必须是非空列表（多面板图至少 1 个子图）")
            if len(panels) > 9:
                raise ValueError(f"slide '{sid}' 的 figure.panels 有 {len(panels)} 个（上限 9，超出请拆分或精简）")
            if layout == "full_figure" and len(panels) > 1:
                raise ValueError(f"slide '{sid}' 的 full_figure 只能包含一个 panel，请改用 multi_figure")
            for pi, p in enumerate(panels):
                if not isinstance(p, dict):
                    raise ValueError(f"slide '{sid}' 的 figure.panels[{pi}] 必须是对象")
                if not (isinstance(p.get("path"), str) and p["path"].strip()):
                    raise ValueError(f"slide '{sid}' 的 figure.panels[{pi}] 缺少 path（每个面板必须指向一个子图）")
        elif layout == "multi_figure":
            raise ValueError(f"slide '{sid}' 的 multi_figure 布局必须有 figure.panels（多面板图）")
        else:
            _need(fig, "path", "figure")   # 无 panels 时顶层 path 必填（单图）
        _need(fig, "caption", "figure")
        if not fig.get("external"):
            _need(fig, "bound_to", "figure")   # 三大可读性保证之一：每图必须指到页内结论（external 装饰图豁免）
            _need(fig, "interpretation", "figure")
        _need(fig, "source", "figure")
    tbl = s.get("table")
    if tbl is not None:
        if not isinstance(tbl, dict):
            raise ValueError(f"slide '{sid}' 的 table 必须是对象")
        if not isinstance(tbl.get("headers"), list) or not tbl["headers"]:
            raise ValueError(f"slide '{sid}' 缺少 table.headers（必填且非空）")
        if not isinstance(tbl.get("rows"), list) or not tbl["rows"]:
            raise ValueError(f"slide '{sid}' 缺少 table.rows（必填且非空）")
        headers = tbl["headers"]
        rows = tbl["rows"]
        if not all(isinstance(row, list) and len(row) == len(headers) for row in rows):
            raise ValueError(f"slide '{sid}' 的 table.rows 必须是与 headers 等长的矩形数组")
        widths = tbl.get("col_widths")
        if widths is not None:
            if (not isinstance(widths, list) or len(widths) != len(headers)
                    or not all(isinstance(width, (int, float)) and math.isfinite(width) and width > 0 for width in widths)):
                raise ValueError(f"slide '{sid}' 的 table.col_widths 必须是与 headers 等长的正数数组")
        if layout == "full_table" and len(tbl["rows"]) > 10:
            raise ValueError(
                f"slide '{sid}' 的 full_table 有 {len(tbl['rows'])} 行数据（上限 10，超出请拆分）")

    # question_answer 布局仅支持 1 个 qa 元素
    if layout == "question_answer":
        n_qa = sum(1 for el in s["body"] if el.get("type") == "qa")
        if n_qa > 1:
            raise ValueError(f"slide '{sid}' 的 question_answer 布局有 {n_qa} 个 qa 元素（最多 1 个）")

def render_slide(prs, s, ctx):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide)
    layout = s.get("layout", "point_figure")
    renderer = LAYOUTS.get(layout, render_point_figure)
    renderer(slide, s, ctx)
    if s.get("speaker_note"):
        notes(slide, s["speaker_note"])

def main(plan_path: str, out_path: str, base_dir: str | None = None) -> None:
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    for s in plan["slides"]:
        _validate_slide(s)
    base = Path(base_dir) if base_dir else Path(plan_path).parent
    fig_dir = base / "assets" / "figures"
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    ctx = {"fig_dir": str(fig_dir)}
    for s in plan["slides"]:
        render_slide(prs, s, ctx)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    prs.save(out_path)
    print(f"已生成: {out_path} ({len(plan['slides'])} 页)")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_path", help="slide_plan.json 路径")
    ap.add_argument("--out", default="final_presentation_cn.pptx")
    ap.add_argument("--base-dir", default=None, help="assets/ 所在目录（默认 plan 所在目录）")
    args = ap.parse_args()
    main(args.plan_path, args.out, args.base_dir)
