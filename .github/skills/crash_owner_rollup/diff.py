# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Compare a current rollup snapshot against the most recent prior snapshot."""

from __future__ import annotations

from typing import Any

CRASH_GROUP_URL = "https://crash.checkmk.com/gui/crashreportgroupview/show/{gid}"


def make_snapshot(routed: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    return {
        "generated_at": generated_at,
        "totals": {
            "groups": len(routed),
            "crashes": sum(int(g["num_crashes"]) for g in routed),
        },
        "groups": {
            str(g["group_id"]): {
                "num_crashes": int(g["num_crashes"]),
                "owner": g.get("owner_email", ""),
                "component": g.get("component_name", ""),
                "matched_path": g.get("matched_path", ""),
            }
            for g in routed
        },
    }


def render_diff(prior: dict[str, Any] | None, current: dict[str, Any]) -> str:
    """Emit a compact 'Changes since <date>' block, or empty string if nothing to say."""
    if prior is None:
        return ""

    prior_groups: dict[int, int] = {int(k): v["num_crashes"] for k, v in prior["groups"].items()}
    cur_groups: dict[int, int] = {int(k): v["num_crashes"] for k, v in current["groups"].items()}

    added = sorted(set(cur_groups) - set(prior_groups))
    removed = sorted(set(prior_groups) - set(cur_groups))
    common = set(prior_groups) & set(cur_groups)
    changed = {
        gid: cur_groups[gid] - prior_groups[gid]
        for gid in common
        if cur_groups[gid] != prior_groups[gid]
    }

    if not (added or removed or changed):
        return ""

    pg, pc = prior["totals"]["groups"], prior["totals"]["crashes"]
    cg, cc = current["totals"]["groups"], current["totals"]["crashes"]

    lines: list[str] = []
    lines.append(
        f"Changes since {prior.get('generated_at', 'last run')}: "
        f"{cg - pg:+d} groups ({pg} → {cg}), {cc - pc:+d} crashes ({pc} → {cc})."
    )

    if removed:
        lines.append(f"Resolved / aged out ({len(removed)}):")
        for gid in sorted(removed, key=lambda g: -prior_groups[g])[:10]:
            lines.append(f"{CRASH_GROUP_URL.format(gid=gid)} (was {prior_groups[gid]})")
        if len(removed) > 10:
            lines.append(f"… and {len(removed) - 10} more")

    if added:
        big = sorted(added, key=lambda g: -cur_groups[g])
        lines.append(f"New ({len(added)}):")
        for gid in big[:10]:
            owner = current["groups"][str(gid)].get("owner", "")
            lines.append(f"{CRASH_GROUP_URL.format(gid=gid)} ({cur_groups[gid]}) [{owner}]")
        if len(added) > 10:
            lines.append(f"… and {len(added) - 10} more")

    if changed:
        lines.append(f"Crash count changed ({len(changed)}):")
        for gid in sorted(changed, key=lambda g: -abs(changed[g]))[:10]:
            lines.append(
                f"{CRASH_GROUP_URL.format(gid=gid)} {prior_groups[gid]} → {cur_groups[gid]} ({changed[gid]:+d})"
            )

    return "\n".join(lines)
