#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import contextlib
import json
import time
from calendar import timegm
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
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.azure_deprecated.agent_based.lib import AZURE_AGENT_SEPARATOR

type Section = Mapping[str | None, Any]


def parse_azure_ad(string_table: StringTable) -> Section:
    parsed: dict[str | None, Any] = {}
    for line in string_table:
        key = line[0]
        value = AZURE_AGENT_SEPARATOR.join(line[1:])
        if key == "users_count":
            with contextlib.suppress(ValueError):
                parsed[None] = {"count": int(value)}
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
    except ValueError, TypeError:
        return None


# .
#   .--user----------------------------------------------------------------.
#   |                                                                      |
#   |                         _   _ ___  ___ _ __                          |
#   |                        | | | / __|/ _ \ '__|                         |
#   |                        | |_| \__ \  __/ |                            |
#   |                         \__,_|___/\___|_|                            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | user accounts                                                        |
#   '----------------------------------------------------------------------'


def discover_ad_users(section: Section) -> DiscoveryResult:
    if None in section:
        yield Service()


def check_azure_users(section: Section) -> CheckResult:
    if not (data := section.get(None)):
        return
    count = data.get("count")
    if count is not None:
        yield from check_levels(
            count,
            "count",
            None,
            human_readable_func=str,
            infoname="User accounts",
        )


agent_section_azure_ad = AgentSection(
    name="azure_ad",
    parse_function=parse_azure_ad,
)


check_plugin_azure_ad = CheckPlugin(
    name="azure_ad",
    service_name="AD Users",
    discovery_function=discover_ad_users,
    check_function=check_azure_users,
)


# .
#   .--sync----------------------------------------------------------------.
#   |                                                                      |
#   |                        ___ _   _ _ __   ___                          |
#   |                       / __| | | | '_ \ / __|                         |
#   |                       \__ \ |_| | | | | (__                          |
#   |                       |___/\__, |_| |_|\___|                         |
#   |                            |___/                                     |
#   +----------------------------------------------------------------------+
#   | AD Connect sync to on-premise directory                              |
#   '----------------------------------------------------------------------'


def discover_sync(section: Section) -> DiscoveryResult:
    # Only discover the service if the sync is enabled
    # There are two keys important for synchronization data
    # onPremisesSyncEnabled: if the sync is enabled at all
    # onPremisesLastSyncDateTime: the actual sync data
    yield from (
        Service(item=key)
        for key, data in section.items()
        if key is not None and data.get("onPremisesSyncEnabled") is not None
    )


def check_azure_sync(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    sync_enabled = data.get("onPremisesSyncEnabled")
    if sync_enabled is None:
        yield Result(state=State.WARN, summary="Synchronization has been disabled")
        return

    sync_time = data.get("onPremisesLastSyncDateTime_parsed")
    if sync_time is None:
        yield Result(state=State.WARN, summary="Has never been synchronized")
        return

    time_delta = time.time() - sync_time

    yield from check_levels(
        time_delta,
        None,
        params.get("age"),
        human_readable_func=render.timespan,
        infoname="Time since last synchronization",
    )


check_plugin_azure_ad_sync = CheckPlugin(
    name="azure_ad_sync",
    service_name="AD Sync %s",
    sections=["azure_ad"],
    discovery_function=discover_sync,
    check_function=check_azure_sync,
    check_ruleset_name="azure_ad",
    check_default_parameters={
        "age": (3600, 7200),
    },
)
