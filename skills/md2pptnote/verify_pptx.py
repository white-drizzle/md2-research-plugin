#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结构校验：python-pptx 重开 PPTX，检查 slide/图片/notes/越界/几何重叠。

用法: python verify_pptx.py final_presentation_cn.pptx
返回 JSON 结构报告。视觉检查由主模型读取实际渲染页图完成，本脚本只检查结构。

重叠检测：
两元素 bbox 相交面积 > 0.02 in² 且超过较小元素面积的 30% → 报重叠
（排除细微边界接触；文本框无父子嵌套，全部两两比较）。
"""
import json, sys
from pptx import Presentation

W_EMU = 12192000   # 13.333 in
H_EMU = 6858000    # 7.5 in
OVERLAP_MIN_AREA = int(0.02 * 914400 * 914400)   # 0.02 in² 换算 EMU²
OVERLAP_RATIO = 0.30


def _bbox(sh):
    try:
        l, t, w, h = sh.left, sh.top, sh.width, sh.height
        if l is None or t is None or w is None or h is None:
            return None
        return (l, t, l + w, t + h)
    except Exception:
        return None


def _intersect_area(a, b):
    """两 bbox (l,t,r,b) 的相交面积（EMU²），不相交返回 0。"""
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0
    return w * h


def _area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def inspect(path: str) -> dict:
    prs = Presentation(path)
    slides = len(prs.slides)
    pictures = 0
    notes_count = 0
    out_of_bounds = 0
    overlaps = 0
    for slide in prs.slides:
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            notes_count += 1
        shapes = list(slide.shapes)
        boxes = []
        for sh in shapes:
            try:
                if sh.shape_type == 13:  # PICTURE
                    pictures += 1
            except Exception:
                pass
            b = _bbox(sh)
            if b is None:
                continue
            l, t, w, h = sh.left, sh.top, sh.width, sh.height
            if l < 0 or t < 0 or (l + w) > W_EMU or (t + h) > H_EMU:
                out_of_bounds += 1
            boxes.append(b)
        # 两两重叠检测
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                inter = _intersect_area(a, b)
                if inter <= OVERLAP_MIN_AREA:
                    continue
                smaller = min(_area(a), _area(b))
                if smaller > 0 and inter / smaller > OVERLAP_RATIO:
                    overlaps += 1
    return {
        "slides": slides,
        "pictures": pictures,
        "notes": notes_count,
        "missing_notes": slides - notes_count,
        "out_of_bounds": out_of_bounds,
        "overlaps": overlaps,
        "ok": out_of_bounds == 0 and (slides - notes_count) == 0 and overlaps == 0
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python verify_pptx.py <file.pptx>")
        sys.exit(1)
    rep = inspect(sys.argv[1])
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    if not rep["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
