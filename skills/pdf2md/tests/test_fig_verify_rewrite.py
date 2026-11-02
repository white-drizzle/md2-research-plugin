# tests/test_fig_verify_rewrite.py
# -*- coding: utf-8 -*-
"""fig_verify.py HTML img 重写与 md5 门控单测。"""
import base64, hashlib, re, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fig_verify as fv


def b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


class RewriteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.imgdir = self.root / "images"
        self.imgdir.mkdir()
        for name, content in [("h1.jpg", "pic-a"), ("h2.jpg", "pic-b"), ("h3.jpg", "pic-c")]:
            (self.imgdir / name).write_bytes(content.encode())

    def tearDown(self):
        self.tmp.cleanup()

    def test_rewrite_by_mapping(self):
        # HTML: Fig7a 放的是 h3(c) 内容（错位），应被纠正为 h1(a)
        html = (f'<img src="data:image/jpeg;base64,{b64("pic-c")}" alt="Fig 7a">'
                f'<img src="data:image/jpeg;base64,{b64("pic-a")}" alt="Fig 7b">')
        mapping = {"h1.jpg": "a", "h2.jpg": "b", "h3.jpg": "c"}
        new = fv.rewrite_html(html, mapping, self.imgdir, alt_prefix="Fig ")
        m = re.search(r'src="data:image/[^"]*base64,([^"]+)"[^>]*alt="Fig 7a"', new)
        self.assertEqual(base64.b64decode(m.group(1)).decode(), "pic-a")

    def test_missing_image_keeps_src(self):
        html = f'<img src="data:image/jpeg;base64,{b64("pic-a")}" alt="Fig 7a">'
        mapping = {"none.jpg": "a"}  # 本地无此图
        new = fv.rewrite_html(html, mapping, self.imgdir, alt_prefix="Fig ")
        self.assertIn(b64("pic-a"), new)  # 保留原样

    def test_rewrite_alt_before_src_order(self):
        # Imp1 回归：alt 在 src 前（属性夹在中间）时，src 数据与 alt 文本不得互换
        html = f'<img alt="Fig 6b" onclick="x()" src="data:image/jpeg;base64,{b64("pic-a")}">'
        mapping = {"h2.jpg": "b"}
        new = fv.rewrite_html(html, mapping, self.imgdir, alt_prefix="Fig ", fig_no=6)
        self.assertIn('alt="Fig 6b"', new)
        self.assertIn('onclick="x()"', new)
        m = re.search(r'src="data:image/[^"]*base64,([^"]+)"', new)
        self.assertEqual(base64.b64decode(m.group(1)).decode(), "pic-b")  # src 被正确替换
        self.assertNotIn(b64("Fig 6b"), new)  # alt 文本未混入 src 数据

    def test_fig_no_scopes_rewrite(self):
        # 回归：Fig6 的 g 映射不得泄漏改写 Fig3g（跨 figure 角标防泄漏）；
        # Fig6g 原 src 是错误内容(pic-a)，应被正确改写为 h2.jpg 内容(pic-b)
        html = (f'<img src="data:image/jpeg;base64,{b64("pic-c")}" alt="Fig 3g">'
                f'<img src="data:image/jpeg;base64,{b64("pic-a")}" alt="Fig 6g">')
        mapping = {"h2.jpg": "g"}  # 来自 Fig6 的核验映射
        new = fv.rewrite_html(html, mapping, self.imgdir, alt_prefix="Fig ", fig_no=6)
        m3 = re.search(r'src="data:image/[^"]*base64,([^"]+)"[^>]*alt="Fig 3g"', new)
        m6 = re.search(r'src="data:image/[^"]*base64,([^"]+)"[^>]*alt="Fig 6g"', new)
        self.assertEqual(base64.b64decode(m3.group(1)).decode(), "pic-c")  # Fig3g 未动
        self.assertEqual(base64.b64decode(m6.group(1)).decode(), "pic-b")  # Fig6g 已改


if __name__ == "__main__":
    unittest.main()
