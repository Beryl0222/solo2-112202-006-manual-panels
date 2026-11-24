"""面板显示约束的测试：字形、行宽、同屏可见与换包方式。"""
import unittest

from pack_check import read_tables
from panel_profile import load_profiles, parse_profile


class HardwareProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = load_profiles(read_tables())

    def test_h1_allows_only_basic_glyph_set(self):
        h1 = self.profiles["H1"]
        self.assertEqual(h1.fit("Espere. Siga"), [])
        self.assertEqual(h1.fit("No siga"), [])
        # 逗号、斜线、重音字母都不在 H1 字形内
        self.assertEqual(h1.fit("Tras vaciar, siga")[0]["kind"], "glyph")
        self.assertTrue(any(i["kind"] == "glyph" for i in h1.fit("a/b")))
        self.assertTrue(any(i["kind"] == "glyph" for i in h1.fit("Atención")))

    def test_h2_allows_slash_and_accents_but_not_comma(self):
        h2 = self.profiles["H2"]
        self.assertEqual(h2.fit("Atención"), [])
        self.assertEqual(h2.fit("a/b"), [])
        self.assertTrue(any(i["kind"] == "glyph" for i in h2.fit("Tras vaciar, siga")))

    def test_width_counts_one_column_per_character(self):
        h1, h2 = self.profiles["H1"], self.profiles["H2"]
        self.assertEqual(h1.fit("Revise llenado"), [])  # 14 列恰好放下
        self.assertEqual(h1.fit("Espere material")[0]["kind"], "width")  # 15 > 14
        self.assertEqual(h2.fit("Aguarde material"), [])  # 16 恰好
        self.assertEqual(h2.fit("Confirmar vaciado")[0]["kind"], "width")  # 17 > 16

    def test_visibility_and_install_mode(self):
        h1, h2 = self.profiles["H1"], self.profiles["H2"]
        self.assertEqual(h1.covisible, frozenset())
        self.assertEqual(h2.covisible, frozenset({("hold", "next")}))
        self.assertEqual(h1.install, "whole")
        self.assertEqual(h2.install, "groups")

    def test_unknown_descriptions_are_rejected(self):
        row = {
            "id": "H9",
            "lines": "1",
            "columns": "8",
            "glyphs": "某种新字形",
            "visible": "一次只见本屏",
            "install": "整包",
        }
        with self.assertRaisesRegex(ValueError, "未登记"):
            parse_profile(row)
        row["glyphs"] = "ASCII 拉丁字母、数字、空格和点"
        row["install"] = "热插拔"
        with self.assertRaisesRegex(ValueError, "未登记"):
            parse_profile(row)


if __name__ == "__main__":
    unittest.main()
