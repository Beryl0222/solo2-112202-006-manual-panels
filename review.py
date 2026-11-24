"""编校：逐屏逐机型核对译员备选，选出可用句或给出冲突。

核对顺序：放不放得下（字形、行宽）→ 保不保义（方向、否定、步骤、对象）→
与工位共用按键说明冲不冲突。同一线体已装或已领的确认键叫法，对等待/停止
方向的屏是硬冲突（值班员转台后会照键名按错），对继续方向的屏记警告。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from semantics import Knowledge, semantic_failures, semantic_notes

#: 从现场记录里提取确认键叫法。
_GLOSS_KEY = re.compile(r"(\S+) 是绿色确认")
_INSTALLED_KEY = [
    re.compile(r"Pulse (\S+) para confirmar"),  # 西语 K 系共享屏原文
    re.compile(r"^(\S+) é a tecla verde"),  # 葡语 K 系共享屏原文
]


def extract_key_names(tables: dict) -> dict:
    """{lang: {键名: 出处列表}}。出处用于冲突报告和回查。"""
    names = {}

    def add(lang, name, origin):
        names.setdefault(lang, {}).setdefault(name, []).append(origin)

    for row in tables["rollouts.tsv"]:
        match = _GLOSS_KEY.search(row["gloss"])
        if match:
            add(row["lang"], match.group(1), f"{row['id']} 现场记录")
    for row in tables["installed_strings.tsv"]:
        if row["group"] != "shared" or row["screen"] != "ok":
            continue
        for pattern in _INSTALLED_KEY:
            match = pattern.search(row["text"])
            if match:
                add(row["lang"], match.group(1), f"{row['rev']} 共享组已装原文")
    return names


@dataclass
class Verdict:
    """一条备选在一款机型上的核对结果。"""

    text: str
    hardware: str
    blockers: list = field(default_factory=list)  # 硬冲突，逐条说明
    warnings: list = field(default_factory=list)  # 可用但需留痕

    @property
    def ok(self):
        return not self.blockers


def judge_variant(profile, requirement, features, text, key_names,
                  conflicting_key_names=False) -> Verdict:
    verdict = Verdict(text=text, hardware=profile.hardware_id)

    for issue in profile.fit(text):
        if issue["kind"] == "glyph":
            verdict.blockers.append(
                f"字形放不下：第 {issue['position']} 位 {issue['char']!r} 超出 {profile.hardware_id} 字形"
            )
        else:
            verdict.blockers.append(
                f"行宽放不下：{issue['length']} 列超过 {profile.hardware_id} 的 {issue['columns']} 列"
            )

    if features is None:
        verdict.blockers.append("未标注语义：知识库无此备选，需先补标注")
        return verdict

    verdict.blockers.extend(semantic_failures(requirement, features))
    verdict.warnings.extend(semantic_notes(requirement, features))

    if (
        conflicting_key_names
        and features.get("key_ref") == "label"
        and text in key_names
    ):
        verdict.warnings.append(
            "现场确认键叫法不一致，按键名写会再加一种叫法，宜用颜色指代"
        )

    direction = requirement["require_direction"]
    lowered = {name.lower(): name for name in key_names}
    hits = [lowered[t.lower()] for t in features.get("tokens", []) if t.lower() in lowered]
    if hits and direction != "confirm":
        # 共享按键说明屏点名按键是本职；其余屏带上键名才有照键名按错的风险。
        if features.get("negation"):
            verdict.warnings.append(f"否定句内含确认键名 {'、'.join(hits)}，需读屏确认")
        elif direction == "proceed":
            verdict.warnings.append(f"继续方向与确认键名 {'、'.join(hits)} 同词，方向一致但需留痕")
        else:
            verdict.blockers.append(
                f"与工位确认键名 {'、'.join(hits)} 冲突：本屏方向是 {direction}，值班员会照键名按错"
            )
    return verdict


def _rank(verdict: Verdict, features: dict):
    steps_kept = len(features.get("steps", [])) if features else 0
    return (len(verdict.warnings), -steps_kept, len(verdict.text))


@dataclass
class ScreenReview:
    bundle: str
    screen: str
    lang: str
    source: str
    selected: dict = field(default_factory=dict)  # hardware -> 选定句
    verdicts: list = field(default_factory=list)  # 全部候选的核对留痕
    conflict: dict | None = None  # 产不出时的冲突说明


def review_strings(tables: dict, profiles: dict, knowledge: Knowledge) -> dict:
    """逐（屏, 语言）编校。返回 {(bundle, screen, lang): ScreenReview}。"""
    key_names = extract_key_names(tables)
    results = {}

    submitted = {(r["bundle"], r["screen"], r["lang"]): r for r in tables["strings.tsv"]}
    langs = sorted({r["lang"] for r in tables["strings.tsv"]})

    targets = list(submitted)
    for bundle, screens in knowledge.expected_screens().items():
        for screen in screens:
            for lang in langs:
                if (bundle, screen, lang) not in submitted:
                    targets.append((bundle, screen, lang))

    for bundle, screen, lang in sorted(targets):
        requirement = knowledge.requirement(bundle, screen)
        row = submitted.get((bundle, screen, lang))
        review = ScreenReview(
            bundle=bundle, screen=screen, lang=lang, source=row["source"] if row else ""
        )
        if row is None:
            review.conflict = {
                "kind": "missing-submission",
                "detail": "译员尚未提交本屏备选",
                "candidates": [],
                "affected_hardware": sorted(profiles),
            }
            results[(bundle, screen, lang)] = review
            continue

        variants = [v for v in row["variants"].split("|") if v]
        conflicting = len(key_names.get(lang, {})) > 1
        for text in variants:
            features = knowledge.features(text)
            for hardware, profile in profiles.items():
                verdict = judge_variant(
                    profile,
                    requirement,
                    features,
                    text,
                    key_names.get(lang, {}),
                    conflicting_key_names=conflicting,
                )
                review.verdicts.append(verdict)

        for hardware, profile in profiles.items():
            usable = [
                (v, knowledge.features(v.text))
                for v in review.verdicts
                if v.hardware == hardware and v.ok
            ]
            if usable:
                best, _ = min(usable, key=lambda pair: _rank(*pair))
                review.selected[hardware] = best.text

        missing_on = [h for h in profiles if h not in review.selected]
        if missing_on:
            review.conflict = {
                "kind": "no-usable-variant",
                "detail": "所有备选在这些机型上均保不住义或放不下",
                "candidates": [
                    {
                        "text": v.text,
                        "hardware": v.hardware,
                        "blockers": v.blockers,
                        "warnings": v.warnings,
                    }
                    for v in review.verdicts
                    if v.hardware in missing_on
                ],
                "affected_hardware": sorted(missing_on),
            }
        results[(bundle, screen, lang)] = review
    return results


def ambiguity_warnings(reviews: dict, profiles: dict, knowledge: Knowledge) -> list:
    """同组内方向相反屏的两两辨认检查（针对已选定的句）。

    等待/停止方向与继续方向的屏两两比对：首词相同则一眼分不出该等还是该按；
    有共用词则留痕待读屏确认。
    """
    warnings = []
    by_group = {}
    for (bundle, screen, lang), review in reviews.items():
        by_group.setdefault((bundle, lang), {})[screen] = review

    holding = {"wait", "stop"}
    going = {"proceed", "conditional-proceed"}
    for (bundle, lang), screens in sorted(by_group.items()):
        directions = {
            screen: knowledge.requirement(bundle, screen)["require_direction"]
            for screen in screens
        }
        pairs = [
            (a, b)
            for a in screens
            for b in screens
            if directions[a] in holding and directions[b] in going
        ]
        for hardware in profiles:
            chosen = {
                screen: r.selected[hardware]
                for screen, r in screens.items()
                if hardware in r.selected
            }
            for left, right in pairs:
                if left not in chosen or right not in chosen:
                    continue
                a, b = chosen[left], chosen[right]
                tokens_a = a.lower().replace(".", " ").split()
                tokens_b = b.lower().replace(".", " ").split()
                shared = sorted(set(tokens_a) & set(tokens_b))
                if tokens_a[0] == tokens_b[0]:
                    warnings.append(
                        {
                            "check": "ambiguity",
                            "hardware": hardware,
                            "lang": lang,
                            "screens": [left, right],
                            "detail": f"首词相同 {tokens_a[0]!r}，一眼分不出该等还是该按",
                        }
                    )
                elif shared:
                    warnings.append(
                        {
                            "check": "shared-token",
                            "hardware": hardware,
                            "lang": lang,
                            "screens": [left, right],
                            "detail": f"{a!r} 与 {b!r} 共用词 {'、'.join(shared)}，需读屏确认",
                        }
                    )
    return warnings
