# tests/test_fig_health_report.py
# -*- coding: utf-8 -*-
"""fig_health.py 链接归属/疑似判定/报告输出单测。"""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fig_health as fh

# 注：Fig2 图注为单面板（a) x.），其下 2 张图 → 链接多 → 疑似（计划 MD 原为
# "a) x; b) y." 与 2 链接恰好相等，无法演示链接多，故最小修正为单面板）
MD = """正文...
![](images/aaa.jpg)
Figure 1. Fabrication.
正文...
![](images/bbb.jpg)
![](images/ccc.jpg)
Figure 2. a) x.
"""


class AssignTest(unittest.TestCase):
    def test_figure_link_assign(self):
        # bbb/ccc 归属 Figure 2（其后最近 caption）；aaa 归属 Figure 1
        figs = fh.parse_full_md(MD)
        self.assertEqual(figs[1]["links"], ["aaa.jpg"])
        self.assertEqual(figs[2]["links"], ["bbb.jpg", "ccc.jpg"])

    def test_suspect_detect(self):
        figs = fh.parse_full_md(MD)
        fh.evaluate(figs)  # 写回 figs[n]["status"] / ["reason"]
        self.assertEqual(figs[1]["status"], "OK")
        self.assertEqual(figs[2]["status"], "疑似")
        self.assertIn("链接多", figs[2]["reason"])

    def test_report_written(self):
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d)
            (raw / "full.md").write_text(MD, encoding="utf-8")
            rc = fh.main(str(raw))
            self.assertEqual(rc, 0)
            rep = (raw / "fig_health.md").read_text(encoding="utf-8")
            self.assertIn("Fig2", rep)
            self.assertIn("疑似", rep)


class EdgeCaseTest(unittest.TestCase):
    def test_trailing_links_after_last_caption(self):
        # 末 caption 之后的链接归文档序最后一个 figure（尾部 flush 分支）
        md = "正文...\n![](images/aaa.jpg)\nFigure 1. x.\n正文...\n![](images/bbb.jpg)"
        figs = fh.parse_full_md(md)
        self.assertEqual(figs[1]["links"], ["aaa.jpg", "bbb.jpg"])

    def test_fewer_links_suspect(self):
        # 链接少：1 链接 vs 2 面板 → 疑似 链接少
        figs = fh.parse_full_md("![](images/aaa.jpg)\nFigure 1. a) x; b) y.")
        fh.evaluate(figs)
        self.assertEqual(figs[1]["status"], "疑似")
        self.assertIn("链接少", figs[1]["reason"])

    def test_empty_md_no_crash(self):
        # 空文档 → 空 dict 不崩溃
        self.assertEqual(fh.parse_full_md(""), {})

    def test_report_warns_no_caption(self):
        # 有图无图注（figs 空 + 图片存在）→ 报告/日志含提示行
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d)
            (raw / "full.md").write_text("![](images/aaa.jpg)\n![](images/bbb.jpg)", encoding="utf-8")
            rc = fh.main(str(raw))
            self.assertEqual(rc, 0)
            rep = (raw / "fig_health.md").read_text(encoding="utf-8")
            self.assertIn("有图无图注", rep)

    def test_report_backs_up_previous(self):
        # S5 回归：覆写前备份旧报告（含 fig_verify 追加段）为 fig_health.prev.md
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d)
            (raw / "full.md").write_text(MD, encoding="utf-8")
            old = "## 纠正记录（fig_verify）\n- {}\n"
            (raw / "fig_health.md").write_text(old, encoding="utf-8")
            rc = fh.main(str(raw))
            self.assertEqual(rc, 0)
            self.assertEqual((raw / "fig_health.prev.md").read_text(encoding="utf-8"), old)
            self.assertIn("Fig2", (raw / "fig_health.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
