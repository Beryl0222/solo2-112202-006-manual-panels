"""拼装与机台判定：合法包、换包方式、并置检查、撤回与回退目标。

工厂以线体、面板型号、语言和当前安装批决定一组合法包。整包机型只能在维护
时整体换；页面组机型可以单换一个组、与其余组的旧词共存，所以必须对实际并
置的旧词新词做辨认检查。人工读屏记录只适用于确切包和并置版本，组合一变即
失效。已发出的更换指令：未装的可撤回，已装的只能安排现场纠正，且不得记成
仍在用旧译。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

#: 读屏记录原文，如 “已人工确认 feed K0 与 shared K0”。
_RECORD = re.compile(r"已人工确认 (\w+) (K\d+) 与 (\w+) (K\d+)")


def next_rev(tables: dict) -> str:
    """在已装版本号之后编下一版，如已有 K0/K1 则得 K2。"""
    numbers = [
        int(row["rev"][1:])
        for row in tables["installed_strings.tsv"]
        if row["rev"].startswith("K") and row["rev"][1:].isdigit()
    ]
    return f"K{max(numbers) + 1 if numbers else 0}"


def compose_groups(reviews: dict, profiles: dict, rev: str) -> dict:
    """把编校结果拼成页面组。组内任一屏无选定句则整组不可发。

    返回 {(lang, hardware, bundle): {"rev", "screens", "ready", "blocked"}}
    """
    groups = {}
    targets = sorted({(r.lang, h, r.bundle) for r in reviews.values() for h in profiles})
    for lang, hardware, bundle in targets:
        screens = {
            screen: review.selected.get(hardware)
            for (b, screen, l), review in reviews.items()
            if b == bundle and l == lang
        }
        blocked = sorted(screen for screen, text in screens.items() if text is None)
        groups[(lang, hardware, bundle)] = {
            "rev": rev,
            "screens": {s: t for s, t in screens.items() if t is not None},
            "ready": not blocked,
            "blocked": blocked,
        }
    return groups


@dataclass
class MachineState:
    rollout_id: str
    line: str
    hardware: str
    lang: str
    phase: str
    bundle_rev: str
    installed: dict = field(default_factory=dict)  # 当前面板各组版本 {group: rev|None}
    received: str | None = None  # 已领未装的版本
    record_combo: dict | None = None  # 读屏记录确认的确切并置组合


def infer_machine_states(tables: dict, profiles: dict) -> list:
    """由领包记录推每台机器当前面板的并置组合。"""
    installed_strings = tables["installed_strings.tsv"]
    states = []
    for row in tables["rollouts.tsv"]:
        state = MachineState(
            rollout_id=row["id"],
            line=row["line"],
            hardware=row["hardware"],
            lang=row["lang"],
            phase=row["phase"],
            bundle_rev=row["bundle_rev"],
        )
        record = _RECORD.search(row["gloss"])
        if record:
            state.record_combo = {record.group(1): record.group(2), record.group(3): record.group(4)}

        if state.phase == "已领未装":
            state.received = row["bundle_rev"]
            # 面板仍跑旧批：用本机现场记录里的确认键叫法反查共享组装机版本。
            gloss_match = re.search(r"(\S+) 是绿色确认", row["gloss"])
            if gloss_match:
                name = gloss_match.group(1)
                for rec in installed_strings:
                    if (
                        rec["group"] == "shared"
                        and rec["lang"] == row["lang"]
                        and name in rec["text"]
                    ):
                        state.installed["shared"] = rec["rev"]
            state.installed.setdefault("feed", None)  # 旧批 feed 屏无记录可查
        elif state.record_combo:
            state.installed = dict(state.record_combo)
        else:
            # 未领 / 装好：bundle_rev 即当前安装批。
            groups = {rec["group"] for rec in installed_strings}
            for group in groups:
                state.installed[group] = row["bundle_rev"]
        states.append(state)
    return states


def combo_texts(combo: dict, lang: str, hardware: str, groups: dict, tables: dict) -> dict:
    """并置组合实际会显示的每屏文字。新组取编校选定句，旧组取已装记录。"""
    texts = {}
    installed = {
        (r["rev"], r["group"], r["lang"], r["screen"]): r["text"]
        for r in tables["installed_strings.tsv"]
    }
    for group, rev in sorted(combo.items()):
        new = groups.get((lang, hardware, group))
        if new and rev == new["rev"]:
            for screen, text in new["screens"].items():
                texts[(group, screen)] = text
            continue
        for (r, g, l, screen), text in installed.items():
            if r == rev and g == group and l == lang:
                texts[(group, screen)] = text
    return texts


def juxtaposition_issues(combo: dict, lang: str, hardware: str, groups: dict,
                         tables: dict, profiles: dict, key_names: dict) -> list:
    """对实际并置的旧词新词做辨认检查：确认键叫法、同屏可见对、缺失记录。"""
    issues = []
    texts = combo_texts(combo, lang, hardware, groups, tables)

    for group, rev in combo.items():
        for screen in _expected_screens(tables, group):
            if (group, screen) not in texts:
                issues.append({
                    "check": "unrecorded",
                    "group": group,
                    "screen": screen,
                    "detail": f"{group} {rev} 的 {screen} 屏无已装记录，并置前需现场读屏",
                })

    lowered = {n.lower(): n for n in key_names.get(lang, {})}
    for (group, screen), text in sorted(texts.items()):
        for token in re.split(r"[\s.,]+", text):
            name = lowered.get(token.lower())
            if name and group != "shared":
                issues.append({
                    "check": "key-collision",
                    "screen": f"{group}/{screen}",
                    "detail": f"{text!r} 含确认键名 {name!r}，与共享按键说明并置时需读屏确认",
                })

    profile = profiles[hardware]
    for left, right in profile.covisible:
        pair = [texts.get(("feed", left)), texts.get(("feed", right))]
        if all(pair):
            a, b = pair[0].lower().split()[0], pair[1].lower().split()[0]
            if a == b:
                issues.append({
                    "check": "ambiguity",
                    "screens": [left, right],
                    "detail": f"同屏可见的两屏首词相同 {a!r}",
                })
    return issues


def _expected_screens(tables: dict, group: str) -> set:
    screens = {r["screen"] for r in tables["installed_strings.tsv"] if r["group"] == group}
    screens |= {r["screen"] for r in tables["strings.tsv"] if r["bundle"] == group}
    return screens


def plan_machines(states: list, groups: dict, profiles: dict, tables: dict,
                  key_names: dict) -> list:
    """逐机台判定：现在能领哪个包、撤不撤得回、已装的怎么纠正、回退到哪套。"""
    plans = []
    for state in states:
        profile = profiles[state.hardware]
        ready_groups = {
            bundle: info
            for (lang, hardware, bundle), info in groups.items()
            if lang == state.lang and hardware == state.hardware and info["ready"]
        }
        plan = {
            "rollout": state.rollout_id,
            "line": state.line,
            "hardware": state.hardware,
            "lang": state.lang,
            "phase": state.phase,
            "install_mode": profile.install,
            "installed": dict(state.installed),
            "issuable": {},
            "action": None,
            "recallable": False,
            "notes": [],
        }

        if profile.install == "whole":
            bundles = {b for (l, h, b) in groups if l == state.lang and h == state.hardware}
            if bundles and all(
                groups[(state.lang, state.hardware, b)]["ready"] for b in bundles
            ):
                plan["issuable"] = {b: groups[(state.lang, state.hardware, b)]["rev"] for b in bundles}
        else:
            plan["issuable"] = {b: i["rev"] for b, i in ready_groups.items()}

        proposed = dict(state.installed)
        proposed.update(plan["issuable"])
        proposed = {g: r for g, r in proposed.items() if r}
        unknown = sorted(g for g, r in state.installed.items() if not r)
        if unknown:
            plan["notes"].append(
                f"当前面板 {'、'.join(unknown)} 组版本无记录可查，并置前需现场读屏"
            )
        if proposed:
            plan["juxtaposition"] = juxtaposition_issues(
                proposed, state.lang, state.hardware, groups, tables, profiles, key_names
            )
        else:
            plan["juxtaposition"] = []

        # 人工读屏记录只适用于确切包和并置版本：组合一变即失效。
        confirmed = {
            tuple(sorted(other.record_combo.items()))
            for other in states
            if other.record_combo
            and other.line == state.line
            and other.hardware == state.hardware
            and other.lang == state.lang
        }
        if proposed and confirmed and tuple(sorted(proposed.items())) not in confirmed:
            plan["notes"].append("拟并置组合不在已确认读屏记录范围内，需补读屏确认")

        if state.phase == "未领":
            plan["action"] = "issue" if plan["issuable"] else "wait"
        elif state.phase == "已领未装":
            plan["recallable"] = True
            plan["action"] = "recall"
            plan["notes"].append(
                f"已领未装的 {state.received} 可整包撤回，待译段齐后重发"
            )
        elif state.phase == "装好":
            plan["action"] = "field-correction" if plan["issuable"] else "monitor"
            if plan["issuable"]:
                plan["notes"].append(
                    "已装机台撤不回，安排现场纠正换入可发组；记录须写明现装版本加待纠正，不得记成仍用旧译"
                )
        elif state.phase == "读屏记录":
            if plan["issuable"]:
                changed = {**state.installed, **plan["issuable"]}
                if changed != state.record_combo:
                    plan["action"] = "hold"
                    plan["notes"].append(
                        "读屏记录只适用于确切并置组合，换入新组即失效；建议维持已确认组合或换后重读屏"
                    )
            else:
                plan["action"] = "keep"

        # 回退目标：同线体同机型同语言最近一套经确认可共存的组合。
        plan["rollback"] = None
        for other in states:
            if (
                other.record_combo
                and other.line == state.line
                and other.hardware == state.hardware
                and other.lang == state.lang
            ):
                plan["rollback"] = dict(other.record_combo)
        plans.append(plan)
    return plans
