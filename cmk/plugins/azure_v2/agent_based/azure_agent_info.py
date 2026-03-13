#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from dataclasses import dataclass, field
from typing import Any, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
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
from cmk.plugins.azure_v2.agent_based.lib import AZURE_AGENT_SEPARATOR


class Params(TypedDict):
    warning_levels: tuple[int, int]
    exception_levels: tuple[int, int]
    resource_pinning: bool


DEFAULT_PARAMS: Params = {
    "warning_levels": (1, 10),
    "exception_levels": (1, 1),
    "resource_pinning": False,
}


@dataclass
class AgentInfo:
    issues: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    agent_bailouts: list[tuple[int, str]] = field(default_factory=list)


def parse_azure_agent_info(string_table: StringTable) -> AgentInfo:
    info = AgentInfo()
    for row in string_table:
        key = row[0]
        value_str = AZURE_AGENT_SEPARATOR.join(row[1:])

        try:
            value = json.loads(value_str)
        except ValueError:
            value = value_str

        if key == "issue":
            info.issues.setdefault(value["type"], []).append(value)
        elif key == "agent-bailout":
            info.agent_bailouts.append(tuple(value))

    return info


def discover_azure_agent_info(section: AgentInfo) -> DiscoveryResult:
    yield Service()


def _check_agent_bailouts(bailouts: list[tuple[int, str]]) -> CheckResult:
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


def _check_agent_issues(issues: dict[str, list[dict[str, Any]]], params: Params) -> CheckResult:
    for type_ in ("warning", "exception"):
        # The next 8 lines exist solely to make mypy happy.
        levels: tuple[int, int] | None
        match type_:
            case "warning":
                levels = params["warning_levels"]
            case "exception":
                levels = params["exception_levels"]
            case _:
                levels = None
        count = len(issues.get(type_, ()))
        yield from check_levels_v1(
            count,
            levels_upper=levels,
            render_func=lambda i: "%d" % i,
            label=f"{type_.title()}s",
        )

    for i in sorted(issues.get("exception", []), key=lambda x: x["msg"]):
        yield Result(
            state=State.OK,
            notice=f"Issue in {i['issued_by']}: Exception: {i['msg']} (!!)",
        )
    for i in sorted(issues.get("warning", []), key=lambda x: x["msg"]):
        yield Result(
            state=State.OK,
            notice=f"Issue in {i['issued_by']}: Warning: {i['msg']} (!)",
        )
    for i in sorted(issues.get("info", []), key=lambda x: x["msg"]):
        yield Result(
            state=State.OK,
            notice=f"Issue in {i['issued_by']}: Info: {i['msg']}",
        )


def check_azure_agent_info(params: Params, section: AgentInfo) -> CheckResult:
    yield from _check_agent_bailouts(section.agent_bailouts)
    yield from _check_agent_issues(section.issues, params)


agent_section_azure_v2_agent_info = AgentSection(
    name="azure_v2_agent_info",
    parse_function=parse_azure_agent_info,
)

check_plugin_azure_v2_agent_info = CheckPlugin(
    name="azure_v2_agent_info",
    service_name="Azure agent info",
    discovery_function=discover_azure_agent_info,
    check_function=check_azure_agent_info,
    check_ruleset_name="azure_v2_agent_info",
    check_default_parameters=DEFAULT_PARAMS,
)
