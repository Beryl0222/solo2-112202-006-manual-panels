"""端到端构建与回查日志测试。"""
import json
import tempfile
import unittest
from pathlib import Path

from build import build
from journal import Journal
from pack_check import DEFAULT_DATA


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls._tmp.name) / "out"
        cls.dashboard = build(DEFAULT_DATA, cls.out)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_outputs_form_per_language_packages(self):
        for lang in ("es", "pt"):
            for hardware in ("H1", "H2"):
                package = json.loads(
                    (self.out / "packages" / lang / f"{hardware}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(package["lang"], lang)
                self.assertEqual(package["rev"], "K2")
                self.assertTrue(package["groups"]["shared"]["ready"])
                self.assertFalse(package["groups"]["feed"]["ready"])

    def test_dashboard_covers_three_views(self):
        self.assertEqual(len(self.dashboard["pending_segments"]), 4)
        self.assertEqual(len(self.dashboard["machines"]), 4)
        rollbacks = {m["rollout"]: m["rollback"] for m in self.dashboard["machines"]}
        self.assertEqual(rollbacks["D4"], {"feed": "K0", "shared": "K0"})
        self.assertIsNone(rollbacks["D1"])

    def test_pending_segments_name_conflict_and_models(self):
        pending = {
            (p["segment"], p["lang"]): p for p in self.dashboard["pending_segments"]
        }
        hold = pending[("feed/hold", "es")]
        self.assertEqual(hold["affected_hardware"], ["H1"])
        self.assertTrue(hold["rejected"])
        missing = pending[("feed/full", "pt")]
        self.assertEqual(missing["kind"], "missing-submission")

    def test_journal_is_queryable_history(self):
        events = Journal.read(self.out / "journal.jsonl")
        self.assertEqual([e["seq"] for e in events], list(range(1, len(events) + 1)))

        journal = Journal()
        journal.events = events
        glyph = journal.query(kind="verdict-blocker", kind_detail="字形放不下")
        self.assertTrue(glyph)
        self.assertTrue(all("text" in e for e in glyph))
        # 字形问题可按机型、语言回查
        self.assertTrue(journal.query(kind="verdict-blocker", hardware="H1", lang="es"))

        conflicts = journal.query(kind="conflict")
        self.assertEqual(len(conflicts), 4)
        actions = {e["rollout"]: e["action"] for e in journal.query(kind="machine-action")}
        self.assertEqual(actions["D1"], "recall")
        self.assertEqual(actions["D2"], "field-correction")
        # 安装范围可回查：每台机可领什么、回退到哪
        d4 = journal.query(kind="machine-action", rollout="D4")[0]
        self.assertEqual(d4["rollback"], {"feed": "K0", "shared": "K0"})

    def test_rebuild_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            again = build(DEFAULT_DATA, Path(tmp) / "out")
        self.assertEqual(self.dashboard, again)


if __name__ == "__main__":
    unittest.main()
