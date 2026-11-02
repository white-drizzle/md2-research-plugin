# -*- coding: utf-8 -*-
"""verify_pptx.py 测试。"""
import sys, tempfile, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import verify_pptx as v

def _make_deck(tmpdir: str, n_slides: int, n_pics: int, notes: bool) -> str:
    """用 python-pptx 造一个已知结构的 pptx。"""
    from pptx import Presentation
    prs = Presentation()
    prs.slide_width = 12192000
    prs.slide_height = 6858000
    for i in range(n_slides):
        s = prs.slides.add_slide(prs.slide_layouts[6])
        if notes:
            s.notes_slide.notes_text_frame.text = f"note {i}"
        if i < n_pics:
            from PIL import Image
            p = os.path.join(tmpdir, f"pic{i}.png")
            Image.new("RGB", (50, 50), "white").save(p)
            s.shapes.add_picture(p, 0, 0, width=914400, height=914400)
    out = os.path.join(tmpdir, "deck.pptx")
    prs.save(out)
    return out

def test_report_structure():
    with tempfile.TemporaryDirectory() as td:
        deck = _make_deck(td, 5, 2, True)
        rep = v.inspect(deck)
        assert rep["slides"] == 5
        assert rep["pictures"] == 2
        assert rep["notes"] == 5

def test_detect_missing_notes():
    with tempfile.TemporaryDirectory() as td:
        deck = _make_deck(td, 3, 0, False)
        rep = v.inspect(deck)
        assert rep["missing_notes"] == 3

def test_bounds_check():
    with tempfile.TemporaryDirectory() as td:
        from pptx import Presentation
        from pptx.util import Inches
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        s = prs.slides.add_slide(prs.slide_layouts[6])
        from pptx.enum.shapes import MSO_SHAPE
        # 越界形状
        s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(14), Inches(1), Inches(2), Inches(2))
        out = os.path.join(td, "oob.pptx")
        prs.save(out)
        rep = v.inspect(out)
        assert rep["out_of_bounds"] == 1

def test_overlap_detected():
    """两图片相交 > 30% 较小元素 → overlaps >= 1。"""
    with tempfile.TemporaryDirectory() as td:
        from pptx import Presentation
        from pptx.util import Inches
        from PIL import Image
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        s = prs.slides.add_slide(prs.slide_layouts[6])
        p = os.path.join(td, "p.png")
        Image.new("RGB", (50, 50), "white").save(p)
        s.shapes.add_picture(p, Inches(1), Inches(1), Inches(3), Inches(3))
        s.shapes.add_picture(p, Inches(2), Inches(1), Inches(3), Inches(3))  # 与上图重叠 2in 宽
        out = os.path.join(td, "ov.pptx")
        prs.save(out)
        rep = v.inspect(out)
        assert rep["overlaps"] >= 1
        assert rep["ok"] is False

def test_overlap_clean_layout():
    """正常布局（不相交）→ overlaps == 0。"""
    with tempfile.TemporaryDirectory() as td:
        from pptx import Presentation
        from pptx.util import Inches
        from PIL import Image
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        s = prs.slides.add_slide(prs.slide_layouts[6])
        s.notes_slide.notes_text_frame.text = "x"
        p = os.path.join(td, "p.png")
        Image.new("RGB", (50, 50), "white").save(p)
        s.shapes.add_picture(p, Inches(1), Inches(1), Inches(3), Inches(3))
        s.shapes.add_picture(p, Inches(5), Inches(1), Inches(3), Inches(3))
        out = os.path.join(td, "cl.pptx")
        prs.save(out)
        rep = v.inspect(out)
        assert rep["overlaps"] == 0
        assert rep["ok"] is True

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("ALL TESTS PASSED")
