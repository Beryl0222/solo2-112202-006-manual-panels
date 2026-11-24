"""编校—拼装—机台判定—看板的一站式构建入口。

只读取资料包，产物写到输出目录：

- ``packages/<lang>/<hardware>.json``  分语言面板包（可交试运行的部分）
- ``reports/pending_segments.json``    待译员处理的译段与冲突
- ``reports/dashboard.json|.md``       班长看板
- ``journal.jsonl``                    可回查的编校与安装范围事件
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dashboard import build_dashboard, render_markdown
from journal import Journal
from pack_check import DEFAULT_DATA, read_tables
from packages import (
    compose_groups,
    infer_machine_states,
    next_rev,
    plan_machines,
)
from panel_profile import load_profiles
from review import ambiguity_warnings, extract_key_names, review_strings
from semantics import Knowledge


def build(directory: Path, out: Path) -> dict:
    tables = read_tables(directory)
    profiles = load_profiles(tables)
    knowledge = Knowledge()
    journal = Journal()

    key_names = extract_key_names(tables)
    for lang, names in sorted(key_names.items()):
        for name, origins in sorted(names.items()):
            journal.record("key-name", lang=lang, name=name, origins=origins)

    reviews = review_strings(tables, profiles, knowledge)
    for (bundle, screen, lang), review in sorted(reviews.items()):
        for verdict in review.verdicts:
            for blocker in verdict.blockers:
                kind = blocker.split("：", 1)[0]
                journal.record(
                    "verdict-blocker",
                    kind_detail=kind,
                    bundle=bundle,
                    screen=screen,
                    lang=lang,
                    hardware=verdict.hardware,
                    text=verdict.text,
                    detail=blocker,
                )
        if review.conflict:
            journal.record(
                "conflict",
                bundle=bundle,
                screen=screen,
                lang=lang,
                conflict=review.conflict["kind"],
                affected_hardware=review.conflict["affected_hardware"],
            )
        for hardware, text in sorted(review.selected.items()):
            journal.record(
                "selection",
                bundle=bundle,
                screen=screen,
                lang=lang,
                hardware=hardware,
                text=text,
            )

    for warning in ambiguity_warnings(reviews, profiles, knowledge):
        journal.record("ambiguity", **warning)

    rev = next_rev(tables)
    groups = compose_groups(reviews, profiles, rev)
    for (lang, hardware, bundle), info in sorted(groups.items()):
        if info["ready"]:
            journal.record(
                "group-ready", lang=lang, hardware=hardware, bundle=bundle, rev=rev
            )
        else:
            journal.record(
                "group-blocked",
                lang=lang,
                hardware=hardware,
                bundle=bundle,
                blocked=info["blocked"],
            )

    states = infer_machine_states(tables, profiles)
    plans = plan_machines(states, groups, profiles, tables, key_names)
    for plan in plans:
        journal.record(
            "machine-action",
            rollout=plan["rollout"],
            line=plan["line"],
            hardware=plan["hardware"],
            lang=plan["lang"],
            action=plan["action"],
            issuable=plan["issuable"],
            recallable=plan["recallable"],
            rollback=plan["rollback"],
        )
        for issue in plan["juxtaposition"]:
            journal.record("juxtaposition", rollout=plan["rollout"], lang=plan["lang"], **issue)

    dashboard = build_dashboard(reviews, groups, plans, rev)

    out.mkdir(parents=True, exist_ok=True)
    (out / "packages").mkdir(exist_ok=True)
    (out / "reports").mkdir(exist_ok=True)

    for (lang, hardware, bundle), info in sorted(groups.items()):
        path = out / "packages" / lang
        path.mkdir(exist_ok=True)
        package_file = path / f"{hardware}.json"
        package = package_file.exists() and json.loads(
            package_file.read_text(encoding="utf-8")
        ) or {"lang": lang, "hardware": hardware, "rev": rev, "groups": {}}
        package["groups"][bundle] = info
        package_file.write_text(
            json.dumps(package, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    (out / "reports" / "pending_segments.json").write_text(
        json.dumps(dashboard["pending_segments"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "reports" / "dashboard.json").write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "reports" / "dashboard.md").write_text(
        render_markdown(dashboard), encoding="utf-8"
    )
    journal.write(out / "journal.jsonl")
    return dashboard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEFAULT_DATA, help="业务资料包路径")
    parser.add_argument("--out", type=Path, default=Path("out"), help="产物输出目录")
    args = parser.parse_args()
    dashboard = build(args.directory, args.out)
    pending = dashboard["pending_segments"]
    print(f"待处理译段 {len(pending)} 条；机台处置 {len(dashboard['machines'])} 台")
    for item in pending:
        print(
            f"  待译：{item['segment']} [{item['lang']}] {item['kind']}"
            f"（型号 {'、'.join(item['affected_hardware'])}）"
        )
    for machine in dashboard["machines"]:
        print(
            f"  机台 {machine['rollout']}：{machine['action']}，"
            f"可领 {machine['issuable_note']}"
        )


if __name__ == "__main__":
    main()
