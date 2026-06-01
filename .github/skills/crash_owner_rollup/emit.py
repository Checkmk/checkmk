# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Render the Slack-ready rollup text (plain text, no markdown bullets)."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

CRASH_GROUP_URL = "https://crash.checkmk.com/gui/crashreportgroupview/show/{gid}"


def short_name(email: str) -> str:
    """email -> @FirstLast (Slack-pastable @-mention placeholder)."""
    local = email.split("@", maxsplit=1)[0]
    return "@" + "".join(p.capitalize() for p in local.split("."))


def _family_from_match(matched: str, check_type: str) -> str:
    if matched:
        m = re.match(r"(?:packages/cmk-plugins/)?cmk/plugins/([^/]+)/", matched)
        if m:
            return m.group(1)
        m = re.match(r"cmk/legacy_checks/([^.]+)\.py", matched)
        if m:
            return m.group(1)
        if "/cmk/checkengine/" in matched:
            return "checkengine"
        if "cmk-ccc" in matched:
            return "ccc"
        if "cmk/utils/" in matched:
            return "utils"
    return check_type or "unknown"


def _short_component(name: str) -> str:
    return re.sub(r"^Plugins?:\s*", "", name).strip()


def render(
    routed_groups: list[dict[str, Any]],
    plugins_coordinator_email: str,
    diff_section: str | None = None,
    min_version_label: str = "2.4",
) -> str:
    """Produce the full Slack-ready text.

    Each routed_groups entry must include:
    group_id, num_crashes, owner_email, component_name, matched_path,
    check_type, plugin_path.
    """
    enriched: list[dict[str, Any]] = []
    for g in routed_groups:
        family = _family_from_match(g.get("matched_path") or "", g.get("check_type") or "")
        owner = g.get("owner_email") or plugins_coordinator_email
        enriched.append({**g, "_family": family, "_owner": owner})

    by_owner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for g in enriched:
        by_owner[g["_owner"]].append(g)

    def totals(entries: list[dict[str, Any]]) -> tuple[int, int]:
        return len(entries), sum(int(e["num_crashes"]) for e in entries)

    other_owners = sorted(
        (em for em in by_owner if em != plugins_coordinator_email),
        key=lambda em: (-totals(by_owner[em])[1], -totals(by_owner[em])[0], em),
    )

    total_groups = sum(totals(v)[0] for v in by_owner.values())
    total_crashes = sum(totals(v)[1] for v in by_owner.values())

    out: list[str] = [
        f"Unsolved Checkmk check crashes on {min_version_label}+ — owner rollup :rotating_light:",
        "",
        (
            f"{total_groups} groups / {total_crashes} crashes — "
            f"after filtering out solved groups, groups whose newest report is on "
            f"{_prev_minor(min_version_label)} or older, and third-party plugins installed "
            f"under a site's local/ directory. Crash count in parens after each link."
        ),
        "",
    ]
    if diff_section:
        out.extend(diff_section.splitlines())
        out.append("")
    out.extend(
        [
            "Investigate any group with:",
            "",
            "```",
            "/crash-report investigate group <group-id>",
            "```",
            "",
        ]
    )

    for em in other_owners:
        out.extend(_render_owner_block(em, by_owner[em], is_coordinator=False))

    if plugins_coordinator_email in by_owner:
        out.extend(
            _render_owner_block(
                plugins_coordinator_email, by_owner[plugins_coordinator_email], is_coordinator=True
            )
        )

    out.append("Ping me if a group belongs elsewhere and I'll reroute.")
    return "\n".join(out)


def _render_owner_block(
    email: str, entries: list[dict[str, Any]], is_coordinator: bool
) -> list[str]:
    n_g = len(entries)
    n_c = sum(int(e["num_crashes"]) for e in entries)
    name = short_name(email)
    out: list[str] = []
    if is_coordinator:
        out.append(
            f"{name} (Plugins coordinator) — unrouted / 3rd-party MKPs / generic — "
            f"{n_g} groups, {n_c} crashes"
        )
        out.append("Please reroute or take into the Plugins backlog.")
    else:
        comps = sorted(
            {_short_component(e["component_name"]) for e in entries if e.get("component_name")}
        )
        comp_str = ", ".join(c for c in comps if c) or "—"
        out.append(f"{name} — {comp_str} — {n_g} groups, {n_c} crashes")

    by_fam: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in entries:
        by_fam[e["_family"]].append(e)
    for fam in sorted(
        by_fam,
        key=lambda f: (-sum(int(x["num_crashes"]) for x in by_fam[f]), -len(by_fam[f]), f),
    ):
        out.append(f"{fam}:")
        for e in sorted(by_fam[fam], key=lambda x: (-int(x["num_crashes"]), int(x["group_id"]))):
            out.append(f"{CRASH_GROUP_URL.format(gid=e['group_id'])} ({e['num_crashes']})")
    out.append("")
    return out


def _prev_minor(version: str) -> str:
    m = re.match(r"^(\d+)\.(\d+)$", version)
    if not m:
        return version
    major, minor = int(m.group(1)), int(m.group(2))
    if minor > 0:
        return f"{major}.{minor - 1}"
    return f"{major}.{minor}"
