#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import json
import time
from calendar import timegm

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.plugins.lib.azure import AZURE_AGENT_SEPARATOR

check_info = {}


def parse_azure_ad(string_table):
    parsed = {}
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


def _str_to_seconds(value):
    try:
        return timegm(time.strptime(value, "%Y-%m-%dT%H:%M:%SZ"))
    except (ValueError, TypeError):
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


def discover_ad_users(parsed):
    if None in parsed:
        yield None, {}


def check_azure_users(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    count = data.get("count")
    if count is not None:
        yield check_levels(
            count,
            "count",
            None,
            unit="User Accounts",
            human_readable_func=int,
        )


check_info["azure_ad"] = LegacyCheckDefinition(
    name="azure_ad",
    parse_function=parse_azure_ad,
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


def discover_sync(parsed):
    # Only discover the service if the sync is enabled
    # There are two keys important for synchronization data
    # onPremisesSyncEnabled: if the sync is enabled at all
    # onPremisesLastSyncDateTime: the actual sync data
    return [
        (key, {})
        for key, data in parsed.items()
        if key is not None and data.get("onPremisesSyncEnabled") is not None
    ]


def check_azure_sync(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    sync_enabled = data.get("onPremisesSyncEnabled")
    if sync_enabled is None:
        yield 1, "Synchronization has been disabled"
        return

    sync_time = data.get("onPremisesLastSyncDateTime_parsed")
    if sync_time is None:
        yield 1, "Has never been synchronized"
        return

    time_delta = time.time() - sync_time
    yield check_levels(
        time_delta,
        None,
        params.get("age"),
        human_readable_func=render.timespan,
        infoname="Time since last synchronization",
    )


check_info["azure_ad.sync"] = LegacyCheckDefinition(
    name="azure_ad_sync",
    service_name="AD Sync %s",
    sections=["azure_ad"],
    discovery_function=discover_sync,
    check_function=check_azure_sync,
    check_ruleset_name="azure_ad",
)
