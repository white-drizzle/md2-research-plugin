# tests/test_fig_health_caption.py
# -*- coding: utf-8 -*-
"""fig_health.py 图注子图计数单测。"""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fig_health as fh


class CountPanelsTest(unittest.TestCase):
    def test_range_writer_a_f(self):
        self.assertEqual(fh.count_panels("Figure 7. ... a) no bending, b) upward, c) downward. d,e) curves."), 5)

    def test_range_dash_a_f(self):
        self.assertEqual(fh.count_panels("Figure 6. a–f) images ...; g) curve; h) bar."), 8)

    def test_enum_only(self):
        self.assertEqual(fh.count_panels("Figure 3. (a) x; (b) y; (c) z."), 3)

    def test_no_panels_single(self):
        self.assertEqual(fh.count_panels("Figure 1. Fabrication process."), 1)

    def test_multi_segment_accumulate(self):
        # a–c + d,e + f 分多段，去重后 6
        self.assertEqual(fh.count_panels("a–c ...; d,e ...; f) ..."), 6)

    def test_parens_prose_trailing_letter(self):
        # (tension)/(compression) 括号内单词尾部 "n)" 不是角标（Bug 1 回归）
        self.assertEqual(fh.count_panels(
            "Figure 7. ... a) no bending, b) upward, c) downward. d,e) curves (tension), ... (compression)."), 5)

    def test_e_g_comma_not_panel_pair(self):
        # "e.g., a" 的 "g,a" 与 "a) x, b)" 的 "x, b" 不应误配成角标对（Bug 2 回归）
        self.assertEqual(fh.count_panels("Figure 4. Various results, e.g., a) x, b) y."), 2)

    def test_empty_caption_single(self):
        self.assertEqual(fh.count_panels(""), 1)

    def test_cross_figure_ref_not_panels(self):
        # 跨图引用 "see Figure 2a-d"：数字前置排除，a–d 不是本图注角标（S1 回归）
        self.assertEqual(fh.count_panels("Figure 5. see Figure 2a-d for detail"), 1)

    def test_group_ending_period(self):
        # "d,e." 句点收尾的成组枚举不漏计（S2 回归）
        self.assertEqual(fh.count_panels("Figure 2. cases d,e."), 2)

    def test_roman_subitems_not_panels(self):
        # Imp2 回归（P9 Fig1 实测）：a) ... i) ii) iii) iv) v) vi) ... b) i) ii) iii,iv)
        # 罗马子项不计入，真实面板 2（a/b）
        cap = ("Figure 1. a) Fabrication process: i) screen printing, ii) NIR drying, "
               "iii) deposition, iv) placement of SMDs, v) NIR soldering, and vi) LED-lit. "
               "b) i) Image of LED array, ii) lit LEDs, and iii,iv) bending modes.")
        self.assertEqual(fh.count_panels(cap), 2)

    def test_roman_subitems_fig8(self):
        # Imp2 回归（P9 Fig8 实测）：a) i) ... ii) ..., b) ... f) —— 真实 6（a–f）
        cap = ("Figure 8. Wearable wireless wound dressing monitoring sensor: "
               "a) i) Sensor configuration and ii) resonant frequency change, "
               "b) image of printed circuit, c) resonant frequency during bending, "
               "d) image of sensor applied onto dressing, e) RF signal change, "
               "and f) resonant frequency as a function of exudate uptake.")
        self.assertEqual(fh.count_panels(cap), 6)

    def test_no_roman_sequence_keeps_i_v_x(self):
        # 无罗马序列时 i)/v) 仍是普通角标（防过度移除）
        self.assertEqual(fh.count_panels("Figure 9. i) one, v) two."), 2)


if __name__ == "__main__":
    unittest.main()
