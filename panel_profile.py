"""面板型号的显示约束：字形集合、行宽、同屏可见组合与换包方式。

hardware.tsv 的 glyphs / visible / install 是现场导出的文字描述，本模块把
已见过的描述解释成可执行的约束。遇到新型号带来的新描述会直接报错，逼项目
在这里显式登记解释规则，保证每款机型的约束可回查、可复用。
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def _is_basic(ch: str) -> bool:
    """ASCII 拉丁字母、数字、空格和点，各占一列。"""
    return ch.isascii() and (ch.isalpha() or ch.isdigit() or ch in " .")


def _is_extended(ch: str) -> bool:
    """H1 字形加斜线和重音字母（拉美葡西文的重音拉丁字母）。"""
    if _is_basic(ch) or ch == "/":
        return True
    return ch.isalpha() and "LATIN" in unicodedata.name(ch, "")


#: glyphs 字段原文 -> 判定函数。新型号的新描述必须在此登记。
GLYPH_CHECKS = {
    "ASCII 拉丁字母、数字、空格和点": _is_basic,
    "H1 加斜线和重音字母": _is_extended,
}

#: install 字段原文 -> 换包方式。whole=维护时整包换；groups=可换单个页面组共存。
INSTALL_MODES = {"整包": "whole", "页面组": "groups"}

_VISIBLE_NONE = "一次只见本屏"
_VISIBLE_PAIR = re.compile(r"^(\w+) 到 (\w+) 可同时见两条$")


@dataclass(frozen=True)
class HardwareProfile:
    """一款面板的显示与换包约束。"""

    hardware_id: str
    lines: int
    columns: int
    glyph_rule: str
    covisible: frozenset  # 可同时可见的屏号对，如 frozenset({("hold", "next")})
    install: str  # "whole" | "groups"

    def allows(self, ch: str) -> bool:
        return GLYPH_CHECKS[self.glyph_rule](ch)

    def fit(self, text: str) -> list:
        """越界或出现无法显示的字都算放不下。返回问题列表，空列表表示放得下。"""
        issues = []
        for position, ch in enumerate(text):
            if not self.allows(ch):
                issues.append(
                    {"kind": "glyph", "char": ch, "position": position, "text": text}
                )
        if len(text) > self.columns:
            issues.append(
                {
                    "kind": "width",
                    "length": len(text),
                    "columns": self.columns,
                    "text": text,
                }
            )
        return issues


def parse_profile(row: dict) -> HardwareProfile:
    """把 hardware.tsv 的一行解释成 HardwareProfile。"""
    glyph_rule = row["glyphs"]
    if glyph_rule not in GLYPH_CHECKS:
        raise ValueError(f"{row['id']} 的字形描述未登记解释规则：{glyph_rule!r}")
    install = row["install"]
    if install not in INSTALL_MODES:
        raise ValueError(f"{row['id']} 的换包方式未登记解释规则：{install!r}")

    visible = row["visible"]
    if visible == _VISIBLE_NONE:
        covisible = frozenset()
    else:
        match = _VISIBLE_PAIR.match(visible)
        if not match:
            raise ValueError(f"{row['id']} 的同屏可见描述未登记解释规则：{visible!r}")
        covisible = frozenset({(match.group(1), match.group(2))})

    return HardwareProfile(
        hardware_id=row["id"],
        lines=int(row["lines"]),
        columns=int(row["columns"]),
        glyph_rule=glyph_rule,
        covisible=covisible,
        install=INSTALL_MODES[install],
    )


def load_profiles(tables: dict) -> dict:
    """hardware.tsv -> {型号: HardwareProfile}。"""
    return {row["id"]: parse_profile(row) for row in tables["hardware.tsv"]}
