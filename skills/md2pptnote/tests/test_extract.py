# -*- coding: utf-8 -*-
"""extract_figures.py 测试：后向归属规则 + 漏图不错位 + caption/引用区分。"""
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import extract_figures as e

def test_backward_assignment_no_shift():
    """核心：图片归属后一个 caption；Fig6 漏图后，Fig6 与 Fig7 之间的图归 Fig7 不错位。"""
    md = """正文 A
![image](https://cdn/x_a.jpg)
Figure 5. Caption five.
Figure 6. Caption six (图被 MinerU 漏了).
正文 B
![image](https://cdn/x_b.jpg)
![image](https://cdn/x_c.jpg)
Figure 7. Caption seven.
"""
    groups = e.extract_figures(md, warn_missing=False)
    g5 = [g for g in groups if g["number"] == 5][0]
    g6 = [g for g in groups if g["number"] == 6][0]
    g7 = [g for g in groups if g["number"] == 7][0]
    assert len(g5["urls"]) == 1 and g5["urls"][0][1].endswith("x_a.jpg")
    # Fig6 漏图：无链接，标记 missing，但编号保留
    assert len(g6["urls"]) == 0 and g6["missing_img"] is True
    # Fig7 的两张图归 Fig7，绝不因 Fig6 空缺前移到 Fig6
    assert [u for _, u in g7["urls"]] == ["https://cdn/x_b.jpg", "https://cdn/x_c.jpg"]

def test_caption_vs_reference():
    """'Figure N.' caption 识别；'Figure N illustrates/presents' 正文引用不误判。"""
    md = """![image](https://cdn/x1.jpg)
Figure 11. Real caption with period.
Figure 11 illustrates a temperature profile, and more text follows here.
![image](https://cdn/x2.jpg)
Figure 12. Real caption.
"""
    groups = e.extract_figures(md, warn_missing=False)
    nums = [g["number"] for g in groups if g["number"] is not None]
    # 只有两个真实 caption（11、12），引用行不是 caption
    assert nums == [11, 12], f"不应把正文引用当 caption: {nums}"
    g11 = [g for g in groups if g["number"] == 11][0]
    assert len(g11["urls"]) == 1 and g11["urls"][0][1].endswith("x1.jpg")

def test_sub_panel_labels():
    """子图标签收集：图片上方 2-4 行的 (b)(c) 标签关联到对应 URL（MinerU 真实布局）。"""
    md = """![image](https://cdn/a.jpg)

(b)
![image](https://cdn/b.jpg)

(c)
![image](https://cdn/c.jpg)
Figure 3. Multi-panel caption.
"""
    groups = e.extract_figures(md, warn_missing=False)
    g3 = [g for g in groups if g["number"] == 3][0]
    urls = [u for _, u in g3["urls"]]
    assert g3["labels"].get(urls[0]) is None, f"第一张图不应有标签(隐含a), got {g3['labels'].get(urls[0])}"
    assert g3["labels"].get(urls[1]) == "(b)", f"b 标签应关联第二图, got {g3['labels']}"
    assert g3["labels"].get(urls[2]) == "(c)", f"c 标签应关联第三图, got {g3['labels']}"

def test_trailing_unclosed_group():
    """文件末尾未闭合的图片（无后续 caption）单独列出，不崩。"""
    md = """正文
![image](https://cdn/x1.jpg)
Figure 1. Caption.
![image](https://cdn/x2.jpg)
![image](https://cdn/x3.jpg)
"""
    groups = e.extract_figures(md, warn_missing=False)
    # 最后一组 number=None（未闭合）
    last = groups[-1]
    assert last["number"] is None
    assert len(last["urls"]) == 2

def test_multiple_figs_multiple_imgs():
    """普通场景：多个 figure 各带多图，顺序归属正确。"""
    md = """![image](https://cdn/1a.jpg)
![image](https://cdn/1b.jpg)
Figure 1. First.
![image](https://cdn/2a.jpg)
Figure 2. Second.
"""
    groups = e.extract_figures(md, warn_missing=False)
    g1 = [g for g in groups if g["number"] == 1][0]
    g2 = [g for g in groups if g["number"] == 2][0]
    assert len(g1["urls"]) == 2
    assert len(g2["urls"]) == 1 and g2["urls"][0][1].endswith("2a.jpg")


def test_to_json_serializable():
    """to_json：图组清单可 JSON 序列化（urls 转 list、labels 并入 images，保留漏图标记）。"""
    import json
    md = """![image](https://cdn/a.jpg)
Figure 1. One.
Figure 2. Missing (漏图).
![image](https://cdn/b.jpg)
Figure 3. Two.
"""
    groups = e.extract_figures(md, warn_missing=False)
    out = e.to_json(groups)
    s = json.dumps(out, ensure_ascii=False)   # 不抛即序列化成功
    assert len(out) == 3
    g1 = out[0]
    assert g1["number"] == 1 and g1["images"][0]["url"].endswith("a.jpg")
    assert out[1]["missing_img"] is True      # Fig2 漏图标记保留
    g3 = out[2]
    assert g3["number"] == 3 and g3["images"][0]["url"].endswith("b.jpg")
    # images 元素含 line/url/label 三键
    assert set(g1["images"][0]) == {"line", "url", "label"}

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("ALL TESTS PASSED")
