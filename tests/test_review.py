"""编校测试：保义、按键冲突、选句与待译冲突。"""
import unittest

from pack_check import read_tables
from panel_profile import load_profiles
from review import ambiguity_warnings, extract_key_names, review_strings
from semantics import Knowledge


class ReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = read_tables()
        cls.profiles = load_profiles(cls.tables)
        cls.knowledge = Knowledge()
        cls.reviews = review_strings(cls.tables, cls.profiles, cls.knowledge)

    def review(self, bundle, screen, lang):
        return self.reviews[(bundle, screen, lang)]

    def test_key_names_come_from_field_records(self):
        names = extract_key_names(self.tables)
        self.assertEqual(set(names["es"]), {"Aceptar", "Siga"})
        self.assertEqual(set(names["pt"]), {"Aceitar"})

    def test_hold_keeps_wait_direction_on_h2(self):
        # “Espere material” 只留等待、把继续交给下一屏，允许。
        self.assertEqual(
            self.review("feed", "hold", "es").selected.get("H2"), "Espere material"
        )

    def test_hold_on_h1_conflicts_with_shared_key_name(self):
        # H1 上唯一放得下的 “Espere. Siga” 撞上西装线确认键名 Siga。
        review = self.review("feed", "hold", "es")
        self.assertNotIn("H1", review.selected)
        self.assertEqual(review.conflict["affected_hardware"], ["H1"])
        reasons = "；".join(
            r for c in review.conflict["candidates"] for r in c["blockers"]
        )
        self.assertIn("Siga", reasons)

    def test_full_screen_must_keep_negation(self):
        review = self.review("feed", "full", "es")
        self.assertEqual(review.selected["H1"], "No siga")
        dropped = [v for v in review.verdicts if v.text == "Revise llenado"]
        self.assertTrue(dropped)
        self.assertTrue(any("否定" in b for v in dropped for b in v.blockers))

    def test_next_screen_has_no_usable_variant(self):
        review = self.review("feed", "next", "es")
        self.assertEqual(review.selected, {})
        self.assertEqual(review.conflict["affected_hardware"], ["H1", "H2"])
        reasons = "；".join(
            r for c in review.conflict["candidates"] for r in c["blockers"]
        )
        self.assertIn("字形", reasons)  # 逗号超字形
        self.assertIn("行宽", reasons)  # 17 列越界
        self.assertIn("丢失方向", reasons)  # Confirmar vaciado 丢了继续许可

    def test_missing_submissions_are_flagged_for_every_model(self):
        for screen in ("full", "next"):
            review = self.review("feed", screen, "pt")
            self.assertEqual(review.conflict["kind"], "missing-submission")
            self.assertEqual(review.conflict["affected_hardware"], ["H1", "H2"])

    def test_unannotated_variant_is_blocked(self):
        tables = read_tables()
        row = next(r for r in tables["strings.tsv"] if r["id"] == "T2")
        row["variants"] = "Adelante ya"  # 知识库没有的新句
        reviews = review_strings(tables, self.profiles, self.knowledge)
        review = reviews[("feed", "run", "es")]
        self.assertEqual(review.selected, {})
        reasons = "；".join(
            r for c in review.conflict["candidates"] for r in c["blockers"]
        )
        self.assertIn("未标注语义", reasons)

    def test_shared_ok_prefers_stable_reference(self):
        # es 现场有两种确认键叫法（Aceptar/Siga），选颜色指代避免再加一种；
        # pt 现场叫法一致（Aceitar），沿用已装键名。
        self.assertEqual(self.review("shared", "ok", "es").selected["H1"], "Tecla verde")
        self.assertEqual(self.review("shared", "ok", "pt").selected["H1"], "Aceitar")

    def test_selected_pairs_are_distinguishable(self):
        warnings = ambiguity_warnings(self.reviews, self.profiles, self.knowledge)
        blocking = [w for w in warnings if w["check"] == "ambiguity"]
        self.assertEqual(blocking, [])
        # es H1 的 run 仍是 Siga，与 K1 键名同词：留痕为共用词警告而非放行
        noted = {(w["hardware"], w["lang"]) for w in warnings}
        self.assertIn(("H1", "es"), noted)


if __name__ == "__main__":
    unittest.main()
