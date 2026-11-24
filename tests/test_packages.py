"""拼装与机台判定测试：合法包、并置检查、撤回与回退。"""
import unittest

from pack_check import read_tables
from packages import (
    compose_groups,
    infer_machine_states,
    next_rev,
    plan_machines,
)
from panel_profile import load_profiles
from review import extract_key_names, review_strings
from semantics import Knowledge


class PackagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = read_tables()
        cls.profiles = load_profiles(cls.tables)
        cls.reviews = review_strings(cls.tables, cls.profiles, Knowledge())
        cls.rev = next_rev(cls.tables)
        cls.groups = compose_groups(cls.reviews, cls.profiles, cls.rev)
        cls.key_names = extract_key_names(cls.tables)
        cls.states = infer_machine_states(cls.tables, cls.profiles)
        cls.plans = {
            p["rollout"]: p
            for p in plan_machines(
                cls.states, cls.groups, cls.profiles, cls.tables, cls.key_names
            )
        }

    def test_new_rev_follows_installed_revs(self):
        self.assertEqual(self.rev, "K2")

    def test_shared_groups_ready_feed_blocked(self):
        self.assertTrue(self.groups[("es", "H1", "shared")]["ready"])
        self.assertTrue(self.groups[("pt", "H2", "shared")]["ready"])
        for lang in ("es", "pt"):
            for hardware in ("H1", "H2"):
                self.assertFalse(self.groups[(lang, hardware, "feed")]["ready"])
        self.assertEqual(
            self.groups[("es", "H1", "feed")]["blocked"], ["hold", "next"]
        )

    def test_uninstalled_machine_is_recallable(self):
        d1 = self.plans["D1"]
        self.assertEqual(d1["action"], "recall")
        self.assertTrue(d1["recallable"])
        self.assertEqual(d1["issuable"], {})  # 整包机型组不齐则无可领包

    def test_installed_machine_gets_field_correction_not_recalled(self):
        d2 = self.plans["D2"]
        self.assertEqual(d2["action"], "field-correction")
        self.assertFalse(d2["recallable"])
        self.assertEqual(d2["issuable"], {"shared": "K2"})
        notes = "；".join(d2["notes"])
        self.assertIn("不得记成仍用旧译", notes)

    def test_unreceived_machine_can_receive_ready_group(self):
        d3 = self.plans["D3"]
        self.assertEqual(d3["action"], "issue")
        self.assertEqual(d3["issuable"], {"shared": "K2"})

    def test_read_screen_record_scopes_exact_combo(self):
        d4 = self.plans["D4"]
        # 记录确认的是 feed K0 + shared K0，换 shared K2 即失效
        self.assertEqual(d4["action"], "hold")
        notes = "；".join(d4["notes"])
        self.assertIn("只适用于确切", notes)

    def test_new_combo_not_covered_by_record(self):
        # D3 拟并置 feed K0 + shared K2，不在东装已确认记录内
        notes = "；".join(self.plans["D3"]["notes"])
        self.assertIn("不在已确认读屏记录范围内", notes)

    def test_juxtaposition_reports_key_collision_and_unrecorded(self):
        checks = {i["check"] for i in self.plans["D2"]["juxtaposition"]}
        self.assertIn("key-collision", checks)  # feed K1 的 Siga 撞上键名
        self.assertIn("unrecorded", checks)  # feed K1 的 hold/next 无记录

    def test_rollback_targets_confirmed_combo(self):
        confirmed = {"feed": "K0", "shared": "K0"}
        self.assertEqual(self.plans["D3"]["rollback"], confirmed)
        self.assertEqual(self.plans["D4"]["rollback"], confirmed)
        self.assertIsNone(self.plans["D1"]["rollback"])
        self.assertIsNone(self.plans["D2"]["rollback"])

    def test_machine_states_infer_installed_revs(self):
        by_id = {s.rollout_id: s for s in self.states}
        self.assertEqual(by_id["D1"].installed.get("shared"), "K0")  # 现场记录反查
        self.assertEqual(by_id["D1"].received, "K1")
        self.assertEqual(by_id["D2"].installed, {"feed": "K1", "shared": "K1"})
        self.assertEqual(by_id["D4"].record_combo, {"feed": "K0", "shared": "K0"})


if __name__ == "__main__":
    unittest.main()
