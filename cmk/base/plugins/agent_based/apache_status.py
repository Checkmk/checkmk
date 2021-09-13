#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
import time
from typing import Any, Dict, Final, Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    get_rate,
    get_value_store,
    Metric,
    register,
    render,
    Result,
    Service,
    State,
)

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Dict[str, Dict[str, float]]

_FIELD_CASTER_MAP: Final = {
    "Uptime": int,
    "IdleWorkers": int,
    "BusyWorkers": int,
    "OpenSlots": int,
    "TotalSlots": int,
    "Total Accesses": int,
    "CPULoad": float,
    "Total kBytes": float,
    "ReqPerSec": float,
    "BytesPerReq": float,
    "BytesPerSec": float,
    "Scoreboard": str,
    "ConnsTotal": int,
    "ConnsAsyncWriting": int,
    "ConnsAsyncKeepAlive": int,
    "ConnsAsyncClosing": int,
    "BusyServers": int,
    "IdleServers": int,
}

_CHECK_LEVEL_ENTRIES: Final = (
    ("Uptime", "Uptime"),
    ("IdleWorkers", "Idle workers"),
    ("BusyWorkers", "Busy workers"),
    ("TotalSlots", "Total slots"),
    ("OpenSlots", "Open slots"),
    ("Total Accesses", "Total access"),
    ("CPULoad", "CPU load"),
    ("Total kBytes", "Total kB"),
    ("ReqPerSec", "Requests per second"),
    ("BytesPerReq", "Bytes per request"),
    ("BytesPerSec", "Bytes per second"),
    ("ConnsTotal", "Total connections"),
    ("ConnsAsyncWriting", "Async writing connections"),
    ("ConnsAsyncKeepAlive", "Async keep alive connections"),
    ("ConnsAsyncClosing", "Async closing connections"),
    ("BusyServers", "Busy servers"),
    ("IdleServers", "Idle servers"),
)

_SCOREBOARD_LABEL_MAP: Final = {  # order is relevant!
    "Waiting": "_",
    "StartingUp": "S",
    "ReadingRequest": "R",
    "SendingReply": "W",
    "Keepalive": "K",
    "DNS": "D",
    "Closing": "C",
    "Logging": "L",
    "Finishing": "G",
    "IdleCleanup": "O",
}


def apache_status_parse_legacy(info: StringTable) -> Section:
    # This parse function is required for compatibility with agents older than the 1.6 release.
    data: Section = {}
    for line in info:
        if len(line) != 4 and not (len(line) == 5 and line[2] == "Total"):
            continue  # Skip unexpected lines
        label = (" ".join(line[2:-1])).rstrip(":")
        caster = _FIELD_CASTER_MAP.get(label)
        if caster is None:
            continue

        address, port = line[:2]
        value = caster(line[-1])
        if port == "None":
            item = address
        else:
            item = "%s:%s" % (address, port)

        if item not in data:
            data[item] = {}

        # Get statistics from scoreboard
        if label == "Scoreboard":
            for stat_label, key in _SCOREBOARD_LABEL_MAP.items():
                data[item]["State_" + stat_label] = value.count(key)
            data[item]["OpenSlots"] = value.count(".")

        data[item][label] = value

        # Count number of total slots after all needed infos are present
        if (
            "OpenSlots" in data[item]
            and "IdleWorkers" in data[item]
            and "BusyWorkers" in data[item]
        ):
            data[item]["TotalSlots"] = (
                data[item]["OpenSlots"] + data[item]["IdleWorkers"] + data[item]["BusyWorkers"]
            )

    return data


def apache_status_parse(string_table: StringTable) -> Section:
    if len(frozenset(len(_) for _ in string_table)) != 1:
        # The separator was changed in 1.6 so that the elements of `info`
        # have a constant length.
        return apache_status_parse_legacy(string_table)

    data: Section = collections.defaultdict(dict)
    for address, port, instance, apache_info in string_table:
        try:
            label, status = apache_info.split(":", 1)
        except ValueError:
            # There is nothing to split.
            continue
        caster = _FIELD_CASTER_MAP.get(label)
        if caster is None:
            # Not a label we handle.
            continue
        value = caster(status)

        if instance and port != "None":
            item = "%s:%s" % (instance, port)
        elif instance:
            item = instance
        elif port != "None":
            item = "%s:%s" % (address, port)
        else:
            item = address

        # Get statistics from scoreboard
        if label == "Scoreboard":
            for stat_label, key in _SCOREBOARD_LABEL_MAP.items():
                data[item]["State_" + stat_label] = value.count(key)
            data[item]["OpenSlots"] = value.count(".")

        data[item][label] = value

        # Count number of total slots after all needed infos are present
        if (
            "OpenSlots" in data[item]
            and "IdleWorkers" in data[item]
            and "BusyWorkers" in data[item]
        ):
            data[item]["TotalSlots"] = (
                data[item]["OpenSlots"] + data[item]["IdleWorkers"] + data[item]["BusyWorkers"]
            )

    return data


register.agent_section(
    name="apache_status",
    parse_function=apache_status_parse,
)


def discover_apache_status(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_apache_status(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if item.endswith(":None"):
        # fix item name discovered before werk 2763
        item = item[:-5]

    data = section.get(item)
    if data is None:
        return

    this_time = int(time.time())
    value_store = get_value_store()

    if "Total Accesses" in data:
        data["ReqPerSec"] = get_rate(
            value_store, "apache_status_%s_accesses" % item, this_time, data.pop("Total Accesses")
        )
    if "Total kBytes" in data:
        data["BytesPerSec"] = get_rate(
            value_store, "apache_status_%s_bytes" % item, this_time, data.pop("Total kBytes") * 1024
        )

    for key, label in ((k, l) for k, l in _CHECK_LEVEL_ENTRIES if k in data):
        value = data[key]
        levels_are_lower = key == "OpenSlots"
        notice_only = key not in {"Uptime", "IdleWorkers", "BusyWorkers", "TotalSlots"}

        renderer = None
        if key == "Uptime":
            renderer = render.timespan
        elif not isinstance(value, float):
            renderer = lambda i: "%d" % int(i)

        yield from check_levels(
            value,
            metric_name=key.replace(" ", "_"),
            levels_lower=params.get(key) if levels_are_lower else None,
            levels_upper=None if levels_are_lower else params.get(key),
            render_func=renderer,
            label=label,
            notice_only=notice_only,
        )

    yield from _scoreboard_results(data)


def _scoreboard_results(data: Dict[str, float]) -> CheckResult:
    # Don't process the scoreboard data directly. Print states instead
    states = []
    for key in _SCOREBOARD_LABEL_MAP:
        value = data.get(f"State_{key}", 0)
        if value > 0:
            states.append(f"{key}: {value}")
        yield Metric(f"State_{key}", value)
    yield Result(state=State.OK, notice="Scoreboard states:\n  %s" % "\n  ".join(states))


register.check_plugin(
    name="apache_status",
    service_name="Apache %s Status",
    discovery_function=discover_apache_status,
    check_function=check_apache_status,
    check_default_parameters={},
    check_ruleset_name="apache_status",
)
