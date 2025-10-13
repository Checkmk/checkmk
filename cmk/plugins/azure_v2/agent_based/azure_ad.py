#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import time
from calendar import timegm
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.azure_v2.agent_based.lib import AZURE_AGENT_SEPARATOR

type Section = Mapping[str | None, Any]


def parse_azure_ad(string_table: StringTable) -> Section:
    parsed: dict[str | None, Any] = {}
    for line in string_table:
        key = line[0]
        value = AZURE_AGENT_SEPARATOR.join(line[1:])
        if key == "users_count":
            try:
                parsed[None] = {"count": int(value)}
            except ValueError:
                pass
        elif key == "ad_connect":
            for data in json.loads(value):
                data["onPremisesLastSyncDateTime_parsed"] = _str_to_seconds(
                    data["onPremisesLastSyncDateTime"]
                )
                item = data["displayName"]
                parsed[item] = data
    return parsed


def _str_to_seconds(value: str) -> int | None:
    try:
        return timegm(time.strptime(value, "%Y-%m-%dT%H:%M:%SZ"))
    except (ValueError, TypeError):
        return None


agent_section_azure_ad = AgentSection(
    name="azure_v2_ad",
    parse_function=parse_azure_ad,
)


def discover_azure_ad_users(section: Section) -> DiscoveryResult:
    if None in section:
        yield Service()


def check_azure_ad_users(section: Section) -> CheckResult:
    if not (data := section.get(None)):
        return

    if count := data.get("count"):
        yield from check_levels(
            value=count,
            metric_name="count",
            render_func=str,
            label="User accounts",
        )


check_plugin_azure_ad_users = CheckPlugin(
    name="azure_v2_ad",
    sections=["azure_v2_ad"],
    service_name="Azure/AD Users",
    discovery_function=discover_azure_ad_users,
    check_function=check_azure_ad_users,
)


def discover_azure_ad_sync(section: Section) -> DiscoveryResult:
    # Only discover the service if the sync is enabled
    # There are two keys important for synchronization data
    # onPremisesSyncEnabled: if the sync is enabled at all
    # onPremisesLastSyncDateTime: the actual sync data
    yield from (
        Service(item=key)
        for key, data in section.items()
        if key is not None and data.get("onPremisesSyncEnabled") is not None
    )


def check_azure_ad_sync(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return

    if data.get("onPremisesSyncEnabled") is None:
        yield Result(state=State.WARN, summary="Synchronization has been disabled")
        return

    if (sync_time := data.get("onPremisesLastSyncDateTime_parsed")) is None:
        yield Result(state=State.WARN, summary="Has never been synchronized")
        return

    time_delta = time.time() - sync_time
    yield from check_levels(
        value=time_delta,
        levels_upper=params.get("age"),
        render_func=render.timespan,
        label="Time since last synchronization",
    )


check_plugin_azure_v2_ad_sync = CheckPlugin(
    name="azure_v2_ad_sync",
    sections=["azure_v2_ad"],
    service_name="Azure/AD Sync %s",
    discovery_function=discover_azure_ad_sync,
    check_function=check_azure_ad_sync,
    check_ruleset_name="azure_v2_ad",
    check_default_parameters={
        "age": ("fixed", (3600, 7200)),
    },
)
