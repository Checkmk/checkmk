#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="index"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="var-annotated"

from __future__ import annotations

import json
import time
from collections.abc import Generator, Iterable, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition, LegacyResult
from cmk.agent_based.v2 import get_value_store, StringTable
from cmk.plugins.azure.lib import AZURE_AGENT_SEPARATOR

check_info = {}


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


def parse_azure_agent_info(string_table: StringTable) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for row in string_table:
        key = row[0]
        value = AZURE_AGENT_SEPARATOR.join(row[1:])

        if key == "remaining-reads":
            _update_remaining_reads(parsed, value)
            continue

        try:
            value = json.loads(value)
        except ValueError:
            pass

        if key == "issue":
            issues = parsed.setdefault("issues", {})
            issues.setdefault(value["type"], []).append(value)
            continue

        if key in ("monitored-groups", "monitored-resources"):
            parsed.setdefault(key, []).extend(value)
            continue

        parsed.setdefault(key, []).append(value)

    return parsed


def discovery_azure_agent_info(
    parsed: dict[str, Any],
) -> Iterable[tuple[None, dict[str, Any]]]:
    yield None, {"discovered_resources": parsed.get("monitored-resources", [])}


def agent_bailouts(bailouts: list[tuple[int, str]]) -> Generator[LegacyResult]:
    now = time.time()
    value_store = get_value_store()
    for status, text in bailouts:
        if text.startswith("Usage client"):
            # Usage API is unreliable.
            # Only use state if this goes on for more than an hour.
            first_seen = value_store.get(text, now)
            value_store[text] = first_seen
            status = 0 if (now - first_seen < 3600) else status
        yield status, text


def remaining_api_reads(reads: int | str, params: Mapping[str, Any]) -> LegacyResult:
    if not isinstance(reads, int):
        return params["remaining_reads_unknown_state"], "Remaining API reads: %s" % reads

    levels = (None, None) + params.get("remaining_reads_levels_lower", (None, None))
    return check_levels(
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
    short_output = []
    long_output = []

    if missing:
        short_output.append("Missing resources: %d" % len(missing))
        long_output.extend("Missing resource: %r(!)" % r for r in missing)
    if new:
        short_output.append("New resources: %d" % len(new))
        long_output.extend("New resource: %r(!)" % r for r in new)

    return ", ".join(short_output), "\n".join(long_output)


def agent_issues(
    issues: dict[str, list[dict[str, Any]]], params: Mapping[str, Any]
) -> Generator[LegacyResult]:
    for type_ in ("warning", "exception"):
        count = len(issues.get(type_, ()))
        yield check_levels(
            count,
            None,
            params.get("%s_levels" % type_),
            human_readable_func=lambda i: "%d" % i,
            infoname="%ss" % type_.title(),
        )

    for i in sorted(issues.get("exception", []), key=lambda x: x["msg"]):
        yield 0, "\nIssue in {}: Exception: {} (!!)".format(i["issued_by"], i["msg"])
    for i in sorted(issues.get("warning", []), key=lambda x: x["msg"]):
        yield 0, "\nIssue in {}: Warning: {} (!)".format(i["issued_by"], i["msg"])
    for i in sorted(issues.get("info", []), key=lambda x: x["msg"]):
        yield 0, "\nIssue in {}: Info: {}".format(i["issued_by"], i["msg"])


def check_azure_agent_info(
    _no_item: None, params: Mapping[str, Any], parsed: dict[str, Any]
) -> Generator[LegacyResult]:
    yield from agent_bailouts(parsed.get("agent-bailout", []))

    reads = parsed.get("remaining-reads")
    if reads is not None:
        yield remaining_api_reads(reads, params)

    groups = parsed.get("monitored-groups")
    if groups:
        yield 0, "Monitored groups: %s" % ", ".join(groups)

    resources = parsed.get("monitored-resources", [])
    resource_infos = resource_pinning(resources, params)
    if resource_infos[0]:
        yield 1, resource_infos[0]

    yield from agent_issues(parsed.get("issues", {}), params)

    if resource_infos[1]:
        yield 0, "\n%s" % resource_infos[1]


check_info["azure_agent_info"] = LegacyCheckDefinition(
    name="azure_agent_info",
    parse_function=parse_azure_agent_info,
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

# TODO: migrate and move to new folder struct
check_info["azure_v2_agent_info"] = LegacyCheckDefinition(
    name="azure_v2_agent_info",
    parse_function=parse_azure_agent_info,
    service_name="Azure Agent Info",
    discovery_function=discovery_azure_agent_info,
    check_function=check_azure_agent_info,
    check_ruleset_name="azure_v2_agent_info",
    check_default_parameters={
        "warning_levels": (1, 10),
        "exception_levels": (1, 1),
        "remaining_reads_unknown_state": 1,
    },
)
