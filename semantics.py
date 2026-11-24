"""语义要求的装载与核对：方向、否定、步骤、动作对象与按键指代。

知识库（knowledge/semantics.json）按屏登记原句必须保住的语义，按备选句登记
译法实际表达的语义。译员下一轮提交新备选时，凡知识库没有标注的句子一律按
“未标注”拦下，逼项目先补标注再编校，保证判断可回查。
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_KNOWLEDGE = Path(__file__).resolve().parent / "knowledge" / "semantics.json"


class Knowledge:
    def __init__(self, path: Path = DEFAULT_KNOWLEDGE):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.screens = data["screens"]
        self.variants = data["variants"]

    def requirement(self, bundle: str, screen: str) -> dict:
        key = f"{bundle}/{screen}"
        if key not in self.screens:
            raise ValueError(f"知识库未登记屏的语义要求：{key}")
        return self.screens[key]

    def features(self, text: str) -> dict | None:
        """备选句的语义标注；未标注返回 None，由编校拦下。"""
        return self.variants.get(text)

    def expected_screens(self) -> dict:
        """{bundle: [screen, ...]}，用于发现整屏未提交的译段。"""
        expected = {}
        for key in self.screens:
            bundle, screen = key.split("/")
            expected.setdefault(bundle, []).append(screen)
        return expected


def semantic_failures(requirement: dict, features: dict) -> list:
    """对照原句要求检查一条备选，返回保义失败原因列表（空为通过）。"""
    failures = []
    direction = requirement["require_direction"]
    if direction not in features.get("directions", []):
        failures.append(f"丢失方向：需要 {direction}")
    if requirement.get("require_negation") and not features.get("negation"):
        failures.append("丢失否定")
    if requirement.get("require_key_ref") and not features.get("key_ref"):
        failures.append("未指向绿色确认键")

    kept = set(features.get("steps", []))
    required = set(requirement.get("steps", []))
    if requirement.get("allow_next_screen_completion"):
        # 当前屏必须独立保留它控制的方向对应步骤，其余允许下一屏补全。
        must_keep = {direction} & required
        if direction == "conditional-proceed":
            must_keep = required
    else:
        must_keep = required
    missing = must_keep - kept
    if missing:
        failures.append(f"丢失步骤：{'、'.join(sorted(missing))}")
    return failures


def semantic_notes(requirement: dict, features: dict) -> list:
    """保义通过但需要留痕的让步：被下一屏补全的步骤、省略的动作对象。"""
    notes = []
    kept = set(features.get("steps", []))
    required = set(requirement.get("steps", []))
    dropped = required - kept
    if dropped and requirement.get("allow_next_screen_completion"):
        notes.append(f"步骤 {'、'.join(sorted(dropped))} 由下一屏补全")
    if features.get("keeps_object") is False:
        notes.append("省略动作对象")
    if features.get("flaw"):
        notes.append(features["flaw"])
    return notes
