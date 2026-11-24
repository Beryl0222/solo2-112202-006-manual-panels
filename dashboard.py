"""班长看板：待处理译段、每款机器现在能领哪个包、冲突后的回退目标。"""
from __future__ import annotations


def build_dashboard(reviews: dict, groups: dict, plans: list, rev: str) -> dict:
    pending = []
    for (bundle, screen, lang), review in sorted(reviews.items()):
        if review.conflict is None:
            continue
        conflict = review.conflict
        entry = {
            "segment": f"{bundle}/{screen}",
            "lang": lang,
            "source": review.source,
            "kind": conflict["kind"],
            "affected_hardware": conflict["affected_hardware"],
            "detail": conflict["detail"],
        }
        if conflict["kind"] == "no-usable-variant":
            entry["rejected"] = [
                {"text": c["text"], "hardware": c["hardware"], "reasons": c["blockers"]}
                for c in conflict["candidates"]
            ]
        pending.append(entry)

    machines = []
    for plan in plans:
        issuable = plan["issuable"]
        if plan["install_mode"] == "whole" and not issuable:
            issuable_note = "整包未齐，暂无可领包"
        elif issuable:
            issuable_note = "、".join(f"{b} 组 {r}" for b, r in sorted(issuable.items()))
        else:
            issuable_note = "无可发组"
        machines.append(
            {
                "rollout": plan["rollout"],
                "line": plan["line"],
                "hardware": plan["hardware"],
                "lang": plan["lang"],
                "phase": plan["phase"],
                "installed": plan["installed"],
                "issuable": issuable,
                "issuable_note": issuable_note,
                "action": plan["action"],
                "recallable": plan["recallable"],
                "rollback": plan["rollback"],
                "notes": plan["notes"],
                "juxtaposition": plan["juxtaposition"],
            }
        )

    return {"new_rev": rev, "pending_segments": pending, "machines": machines}


def render_markdown(dashboard: dict) -> str:
    lines = [f"# 班长看板（新包版本 {dashboard['new_rev']}）", "", "## 待处理译段"]
    if not dashboard["pending_segments"]:
        lines.append("（无）")
    for item in dashboard["pending_segments"]:
        lines.append(
            f"- {item['segment']} [{item['lang']}] {item['source'] or '（未提交）'}"
            f"——{item['kind']}，受影响型号：{'、'.join(item['affected_hardware'])}"
        )
        for rejected in item.get("rejected", []):
            reasons = "；".join(rejected["reasons"])
            lines.append(f"  - {rejected['hardware']} 退 {rejected['text']!r}：{reasons}")

    lines += ["", "## 每款机器现在能领哪个包"]
    for machine in dashboard["machines"]:
        lines.append(
            f"- {machine['rollout']}（{machine['line']} {machine['hardware']} "
            f"[{machine['lang']}]，{machine['phase']}）：{machine['issuable_note']}"
            f"；处置：{machine['action']}"
        )
        for note in machine["notes"]:
            lines.append(f"  - {note}")
        for issue in machine["juxtaposition"]:
            lines.append(f"  - 并置{issue['check']}：{issue['detail']}")

    lines += ["", "## 安装后发现冲突时的回退目标"]
    for machine in dashboard["machines"]:
        if machine["rollback"]:
            combo = "、".join(f"{g} {r}" for g, r in sorted(machine["rollback"].items()))
            lines.append(f"- {machine['rollout']}：恢复 {combo}（经确认可共存）")
        else:
            lines.append(f"- {machine['rollout']}：无已确认组合，需现场读屏后才能定回退目标")
    lines.append("")
    return "\n".join(lines)
