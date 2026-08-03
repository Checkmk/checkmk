#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import contextlib
import json
import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.azure_deprecated.agent_based.lib import AZURE_AGENT_SEPARATOR

type Section = Mapping[str, Any]


def _update_remaining_reads(parsed: dict[str, Any], value: str) -> None:
    """parse remaining API reads

    The key 'remaining-reads' can be present multiple times,
    or not at all.
    Three cases are considered:
     * 'remaining-reads' not present -> not in parsed
     * present, but never an integer -> 'unknown'
     * at least one integer value -> minimum of all values
    """
    try:
        if isinstance(parsed.setdefault("remaining-reads", "unknown"), int):
            parsed["remaining-reads"] = min(int(value), parsed["remaining-reads"])
        else:
            parsed["remaining-reads"] = int(value)
    except ValueError:
        pass


def parse_azure_agent_info(string_table: StringTable) -> Section:
    parsed: dict[str, Any] = {}
    for row in string_table:
        key = row[0]
        value: Any = AZURE_AGENT_SEPARATOR.join(row[1:])

        if key == "remaining-reads":
            _update_remaining_reads(parsed, value)
            continue

        with contextlib.suppress(ValueError):
            value = json.loads(value)

        if key == "issue":
            issues = parsed.setdefault("issues", {})
            issues.setdefault(value["type"], []).append(value)
            continue

        if key in ("monitored-groups", "monitored-resources"):
            parsed.setdefault(key, []).extend(value)
            continue

        parsed.setdefault(key, []).append(value)

    return parsed


def discovery_azure_agent_info(section: Section) -> DiscoveryResult:
    yield Service(parameters={"discovered_resources": section.get("monitored-resources", [])})


def agent_bailouts(bailouts: list[tuple[int, str]]) -> CheckResult:
    now = time.time()
    value_store = get_value_store()
    for status, text in bailouts:
        if text.startswith("Usage client"):
            # Usage API is unreliable.
            # Only use state if this goes on for more than an hour.
            first_seen = value_store.get(text, now)
            value_store[text] = first_seen
            status = 0 if (now - first_seen < 3600) else status
        yield Result(state=State(status), summary=text)


def remaining_api_reads(reads: int | str, params: Mapping[str, Any]) -> CheckResult:
    if not isinstance(reads, int):
        yield Result(
            state=State(params["remaining_reads_unknown_state"]),
            summary=f"Remaining API reads: {reads}",
        )
        return

    levels = (None, None) + params.get("remaining_reads_levels_lower", (None, None))
    yield from check_levels(
        reads,
        "remaining_reads",
        levels,
        infoname="Remaining API reads",
        human_readable_func=lambda i: "%d" % i,
        boundaries=(0, 15000),
    )


def resource_pinning(present_resources: list[str], params: Mapping[str, Any]) -> tuple[str, str]:
    if not params.get("resource_pinning"):
        return "", ""

    discovered = params.get("discovered_resources")
    if discovered is None:
        return "", ""

    missing = sorted(set(discovered) - set(present_resources))
    new = sorted(set(present_resources) - set(discovered))
    short_output: list[str] = []
    long_output: list[str] = []

    if missing:
        short_output.append(f"Missing resources: {len(missing)}")
        long_output.extend(f"Missing resource: {r!r}(!)" for r in missing)
    if new:
        short_output.append(f"New resources: {len(new)}")
        long_output.extend(f"New resource: {r!r}(!)" for r in new)

    return ", ".join(short_output), "\n".join(long_output)


def agent_issues(issues: dict[str, list[dict[str, Any]]], params: Mapping[str, Any]) -> CheckResult:
    for type_ in ("warning", "exception"):
        count = len(issues.get(type_, ()))
        yield from check_levels(
            count,
            None,
            params.get(f"{type_}_levels"),
            human_readable_func=lambda i: "%d" % i,
            infoname=f"{type_.title()}s",
        )

    for i in sorted(issues.get("exception", []), key=lambda x: x["msg"]):
        yield Result(
            state=State.OK, notice=f"Issue in {i['issued_by']}: Exception: {i['msg']} (!!)"
        )
    for i in sorted(issues.get("warning", []), key=lambda x: x["msg"]):
        yield Result(state=State.OK, notice=f"Issue in {i['issued_by']}: Warning: {i['msg']} (!)")
    for i in sorted(issues.get("info", []), key=lambda x: x["msg"]):
        yield Result(state=State.OK, notice=f"Issue in {i['issued_by']}: Info: {i['msg']}")


def check_azure_agent_info(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from agent_bailouts(section.get("agent-bailout", []))

    reads = section.get("remaining-reads")
    if reads is not None:
        yield from remaining_api_reads(reads, params)

    groups = section.get("monitored-groups")
    if groups:
        yield Result(state=State.OK, summary=f"Monitored groups: {', '.join(groups)}")

    resources = section.get("monitored-resources", [])
    resource_infos = resource_pinning(resources, params)
    if resource_infos[0]:
        yield Result(state=State.WARN, summary=resource_infos[0])

    yield from agent_issues(section.get("issues", {}), params)

    if resource_infos[1]:
        yield Result(state=State.OK, notice=resource_infos[1])


agent_section_azure_agent_info = AgentSection(
    name="azure_agent_info",
    parse_function=parse_azure_agent_info,
)


check_plugin_azure_agent_info = CheckPlugin(
    name="azure_agent_info",
    service_name="Azure Agent Info",
    discovery_function=discovery_azure_agent_info,
    check_function=check_azure_agent_info,
    check_ruleset_name="azure_agent_info",
    check_default_parameters={
        "warning_levels": (1, 10),
        "exception_levels": (1, 1),
        "remaining_reads_unknown_state": 1,
    },
)
