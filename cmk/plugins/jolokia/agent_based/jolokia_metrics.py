#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.agent_based.v2 import (
    check_levels as check_levels_v2,
)
from cmk.plugins.jolokia.agent_based.lib import (
    get_inventory_jolokia_metrics_apps,
    jolokia_metrics_parse,
)

# Example output from agent:
# <<<jolokia_metrics>>>
# 8080 NonHeapMemoryUsage 101078952
# 8080 NonHeapMemoryMax 184549376
# 8080 HeapMemoryUsage 2362781664
# 8080 HeapMemoryMax 9544663040
# 8080 ThreadCount 78
# 8080 DeamonThreadCount 72
# 8080 PeakThreadCount 191
# 8080 TotalStartedThreadCount 941
# 8080 Uptime 572011375
# 8080,java.lang:name=PS_MarkSweep,type=GarbageCollector CollectionCount 0


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except TypeError, ValueError:
        return 0


def parse_jolokia_metrics(string_table: StringTable) -> StringTable:
    return string_table


agent_section_jolokia_metrics = AgentSection(
    name="jolokia_metrics",
    parse_function=parse_jolokia_metrics,
)

# .
#   .--Arcane helpers------------------------------------------------------.
#   |                     _                                                |
#   |                    / \   _ __ ___ __ _ _ __   ___                    |
#   |                   / _ \ | '__/ __/ _` | '_ \ / _ \                   |
#   |                  / ___ \| | | (_| (_| | | | |  __/                   |
#   |                 /_/   \_\_|  \___\__,_|_| |_|\___|                   |
#   |                                                                      |
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | TODO: See if these can be removed altogether                         |
#   '----------------------------------------------------------------------'


# This bisects the app server and its values
def jolokia_metrics_app(info, split_item):
    inst, app = split_item
    parsed = jolokia_metrics_parse(info)
    if parsed.get(inst, "") is None:
        raise IgnoreResultsError("No information from Jolokia agent")
    if inst not in parsed or app not in parsed[inst].get("apps", {}):
        return None
    return parsed[inst]["apps"][app]


# This bisects info from BEA and passes on to jolokia_metrics_app
def jolokia_metrics_serv(info, split_item):
    inst, app, serv = split_item
    app = jolokia_metrics_app(info, (inst, app))
    if not app or serv not in app.get("servlets", {}):
        return None
    return app["servlets"][serv]


# .
#   .--Number of Requests--------------------------------------------------.
#   |               ____                            _                      |
#   |              |  _ \ ___  __ _ _   _  ___  ___| |_ ___                |
#   |              | |_) / _ \/ _` | | | |/ _ \/ __| __/ __|               |
#   |              |  _ <  __/ (_| | |_| |  __/\__ \ |_\__ \               |
#   |              |_| \_\___|\__, |\__,_|\___||___/\__|___/               |
#   |                            |_|                                       |
#   '----------------------------------------------------------------------'


def discover_jolokia_metrics_serv(section: StringTable) -> DiscoveryResult:
    parsed = jolokia_metrics_parse(section)
    needed_key = "Requests"
    for inst, vals in parsed.items():
        if vals is None:
            continue  # type: ignore[unreachable]  # no data from agent
        for app, val in vals.get("apps", {}).items():
            for serv, servinfo in val.get("servlets", {}).items():
                if needed_key in servinfo:
                    yield Service(item=f"{inst} {app} {serv}")


def check_jolokia_metrics_serv_req(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    serv = jolokia_metrics_serv(section, item.split())
    if not serv or "Requests" not in serv:
        return

    req = saveint(serv["Requests"])

    yield from check_levels_v2(
        req,
        metric_name="Requests",
        levels_upper=params["levels_upper"],
        levels_lower=params["levels_lower"],
        render_func=str,
        label="Requests",
    )

    try:
        request_rate = get_rate(get_value_store(), "rate", time.time(), req, raise_overflow=True)
    except GetRateError:
        return

    yield from check_levels_v2(
        request_rate,
        metric_name="RequestRate",
        render_func=lambda x: f"{x:.2f}",
        label="Request rate",
    )


check_plugin_jolokia_metrics_serv_req = CheckPlugin(
    name="jolokia_metrics_serv_req",
    service_name="JVM %s Requests",
    sections=["jolokia_metrics"],
    discovery_function=discover_jolokia_metrics_serv,
    check_function=check_jolokia_metrics_serv_req,
    check_ruleset_name="jvm_requests",
    check_default_parameters={
        "levels_lower": ("no_levels", None),
        "levels_upper": ("fixed", (5000, 6000)),
    },
)

# .
#   .--App state-----------------------------------------------------------.
#   |                _                      _        _                     |
#   |               / \   _ __  _ __    ___| |_ __ _| |_ ___               |
#   |              / _ \ | '_ \| '_ \  / __| __/ _` | __/ _ \              |
#   |             / ___ \| |_) | |_) | \__ \ || (_| | ||  __/              |
#   |            /_/   \_\ .__/| .__/  |___/\__\__,_|\__\___|              |
#   |                    |_|   |_|                                         |
#   '----------------------------------------------------------------------'


def check_jolokia_metrics_app_state(item: str, section: StringTable) -> CheckResult:
    app_state = 3
    app = jolokia_metrics_app(section, item.split())

    # FIXME: this could be nicer.
    if app and "Running" in app:
        app_state = 0 if app["Running"] == "1" else 2
    # wenn in app statename steht
    elif app and "stateName" in app:
        app_state = 0 if app["stateName"] == "STARTED" else 2
    if app_state == 3:
        yield Result(state=State.UNKNOWN, summary="data not found in agent output")
        return
    if app_state == 0:
        yield Result(state=State.OK, summary="application is running")
        return
    if app_state == 2:
        yield Result(state=State.CRIT, summary="application is not running (Running: %s)")
        return

    yield Result(state=State.UNKNOWN, summary="error in agent output")
    return


check_plugin_jolokia_metrics_app_state = CheckPlugin(
    name="jolokia_metrics_app_state",
    service_name="JVM %s State",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps(
        "app_state", needed_keys={"Running", "stateName"}
    ),
    check_function=check_jolokia_metrics_app_state,
)

# .
#   .--Unsorted------------------------------------------------------------.
#   |              _   _                      _           _                |
#   |             | | | |_ __  ___  ___  _ __| |_ ___  __| |               |
#   |             | | | | '_ \/ __|/ _ \| '__| __/ _ \/ _` |               |
#   |             | |_| | | | \__ \ (_) | |  | ||  __/ (_| |               |
#   |              \___/|_| |_|___/\___/|_|   \__\___|\__,_|               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_jolokia_metrics_app_sess(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    if len(item.split()) == 3:
        app = jolokia_metrics_serv(section, item.split())
    elif len(item.split()) == 2:
        app = jolokia_metrics_app(section, item.split())
    if not app:  # type: ignore[possibly-undefined]
        return

    sessions = app.get("Sessions", app.get("activeSessions", app.get("OpenSessionsCurrentCount")))
    if sessions is None:
        return

    sess = saveint(sessions)
    maxActive = saveint(
        app.get("Sessions", app.get("maxActiveSessions", app.get("OpenSessionsCurrentCount")))
    )

    yield from check_levels_v2(
        sess,
        metric_name="sessions",
        levels_upper=params["levels_upper"],
        levels_lower=params["levels_lower"],
        render_func=str,
        label="Sessions",
    )

    if maxActive and maxActive > 0:
        yield Result(state=State.OK, summary=f"Maximum active sessions: {maxActive}")


def check_jolokia_metrics_bea_queue(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    app = jolokia_metrics_app(section, item.split())
    if not app:
        yield Result(state=State.UNKNOWN, summary="application not found")
        return

    if (length := app.get("QueueLength")) is None:
        return

    yield from check_levels_v2(
        int(length),
        metric_name="length",
        levels_upper=params["levels_upper"],
        render_func=str,
        label="Queue length",
    )


def check_request_count(item, info, value_store):
    """
    "CompletedRequestCount" and "requestCount" are specifically queried by our agent,
    (see the constant QUERY_SPECS_SPECIFIC_LEGACY).

    CompletedRequestCount -> weblogic of BEA system; it is the total number of requests
    (https://docs.oracle.com/middleware/1213/wls/WLMBR/core/index.html)

    requestCount -> tomcat servers; it is per second
    (https://docs.tibco.com/pub/sftm/6.0.0/doc/html/GUID-5738EB01-D159-4D0D-9F3B-22663B2D6756.html)
    """

    if not (app := jolokia_metrics_app(info, item.split())):
        return

    if (completed_request_count := app.get("CompletedRequestCount")) is not None:
        rate = get_rate(
            value_store,
            "j4p.bea.requests.%s" % item,
            time.time(),
            int(completed_request_count),
            raise_overflow=True,
        )
        yield Result(state=State.OK, summary="%.2f requests/sec" % rate)
        yield Metric("rate", rate)

    elif (request_count := app.get("requestCount")) is not None:
        yield Result(state=State.OK, summary="%.2f requests/sec" % int(request_count))
        yield Metric("rate", int(request_count))


def check_jolokia_metrics_bea_requests(item: str, section: StringTable) -> CheckResult:
    yield from check_request_count(item, section, get_value_store())


def check_jolokia_metrics_bea_threads(item: str, section: StringTable) -> CheckResult:
    app = jolokia_metrics_app(section, item.split())
    if not app:
        yield Result(state=State.UNKNOWN, summary="data not found in agent output")
        return

    metrics = []
    infos = []
    for varname, title in [
        ("ExecuteThreadTotalCount", "total"),
        ("ExecuteThreadIdleCount", "idle"),
        ("StandbyThreadCount", "standby"),
        ("HoggingThreadCount", "hogging"),
    ]:
        if varname not in app:
            continue

        value = int(app[varname])
        metrics.append(Metric(varname, value))
        infos.append("%s: %d" % (title, value))

    if not infos:
        yield Result(state=State.UNKNOWN, summary="no metrics found in the data")
        return

    yield Result(state=State.OK, summary=", ".join(infos))
    yield from metrics


check_plugin_jolokia_metrics_app_sess = CheckPlugin(
    name="jolokia_metrics_app_sess",
    service_name="JVM %s Sessions",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps(
        "app_sess", needed_keys={"Sessions", "activeSessions"}
    ),
    check_function=check_jolokia_metrics_app_sess,
    check_ruleset_name="jvm_sessions",
    check_default_parameters={
        "levels_lower": ("no_levels", None),
        "levels_upper": ("fixed", (800, 1000)),
    },
)


check_plugin_jolokia_metrics_requests = CheckPlugin(
    name="jolokia_metrics_requests",
    service_name="JVM %s Requests",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps("requests", needed_keys={"requestCount"}),
    check_function=check_jolokia_metrics_bea_requests,
)


check_plugin_jolokia_metrics_bea_queue = CheckPlugin(
    name="jolokia_metrics_bea_queue",
    service_name="JVM %s Queue",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps("queue", needed_keys={"QueueLength"}),
    check_function=check_jolokia_metrics_bea_queue,
    check_ruleset_name="jvm_queue",
    check_default_parameters={
        "levels_upper": ("fixed", (20, 50)),
    },
)


check_plugin_jolokia_metrics_bea_requests = CheckPlugin(
    name="jolokia_metrics_bea_requests",
    service_name="JVM %s Requests",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps(
        "bea_requests", needed_keys={"CompletedRequestCount"}
    ),
    check_function=check_jolokia_metrics_bea_requests,
)


check_plugin_jolokia_metrics_bea_threads = CheckPlugin(
    name="jolokia_metrics_bea_threads",
    service_name="JVM %s Threads",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps(
        "threads", needed_keys={"StandbyThreadCount"}
    ),
    check_function=check_jolokia_metrics_bea_threads,
)


check_plugin_jolokia_metrics_bea_sess = CheckPlugin(
    name="jolokia_metrics_bea_sess",
    service_name="JVM %s Sessions",
    sections=["jolokia_metrics"],
    discovery_function=get_inventory_jolokia_metrics_apps(
        "bea_app_sess", needed_keys={"OpenSessionsCurrentCount"}
    ),
    check_function=check_jolokia_metrics_app_sess,
    check_ruleset_name="jvm_sessions",
    check_default_parameters={
        "levels_lower": ("no_levels", None),
        "levels_upper": ("fixed", (800, 1000)),
    },
)


def inventory_jolokia_metrics_cache(metrics, info):
    parsed = jolokia_metrics_parse(info)
    metrics_set = set(metrics)
    for inst, vals in [x for x in parsed.items() if x[1] is not None]:  # type: ignore[redundant-expr]
        for cache, cache_vars in vals.get("CacheStatistics", {}).items():
            if metrics_set.intersection(cache_vars) == metrics_set:
                yield f"{inst} {cache}", {}


def check_jolokia_metrics_cache(metrics, totals, item, info):
    type_map = {
        "CacheHitPercentage": (float, 100.0, "%.1f%%"),
        "InMemoryHitPercentage": (float, 100.0, "%.1f%%"),
        "OnDiskHitPercentage": (float, 100.0, "%.1f%%"),
        "OffHeapHitPercentage": (float, 100.0, "%.1f%%"),
    }

    parsed = jolokia_metrics_parse(info)
    try:
        inst, cache = item.split(" ")

        # we display the "metrics" first, totals after, but to "fix" metrics based on zero-totals
        # we need to go over the totals once
        for total in totals:
            val: float | int = int(parsed[inst]["CacheStatistics"][cache][total])
            if val != 0:
                break

        for metric in metrics:
            type_, scale, format_str = type_map.get(metric, (int, 1, "%d"))

            val = type_(parsed[inst]["CacheStatistics"][cache][metric]) * scale
            if isinstance(val, float) and val == 0.0:
                # what a hack! we assume the float is based on the totals (all of them) and if they
                # were all 0, so this float is 0/0, we want to display it as 1 as to not cause
                # an alert
                val = 1.0 * scale
            yield Result(state=State.OK, summary=("%s: " + format_str) % (metric, val))
            yield Metric(metric, val)

        for total in totals:
            type_, scale, format_str = type_map.get(total, (int, 1, "%d"))
            val = type_(parsed[inst]["CacheStatistics"][cache][total]) * scale
            yield Result(state=State.OK, summary=("%s: " + format_str) % (total, val))
    except KeyError:
        # some element of the item was missing
        pass


def discover_jolokia_metrics_cache_hits(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=item, parameters=parameters)
        for (item, parameters) in inventory_jolokia_metrics_cache(
            ["CacheHitPercentage", "ObjectCount", "CacheHits", "CacheMisses"], section
        )
    ]


def check_jolokia_metrics_cache_hits(item: str, section: StringTable) -> CheckResult:
    yield from check_jolokia_metrics_cache(
        ["CacheHitPercentage", "ObjectCount"], ["CacheHits", "CacheMisses"], item, section
    )


check_plugin_jolokia_metrics_cache_hits = CheckPlugin(
    name="jolokia_metrics_cache_hits",
    service_name="JVM %s Cache Usage",
    sections=["jolokia_metrics"],
    discovery_function=discover_jolokia_metrics_cache_hits,
    check_function=check_jolokia_metrics_cache_hits,
)


def discover_jolokia_metrics_in_memory(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=item, parameters=parameters)
        for (item, parameters) in inventory_jolokia_metrics_cache(
            ["InMemoryHitPercentage", "MemoryStoreObjectCount", "InMemoryHits", "InMemoryMisses"],
            section,
        )
    ]


def check_jolokia_metrics_in_memory(item: str, section: StringTable) -> CheckResult:
    yield from check_jolokia_metrics_cache(
        ["InMemoryHitPercentage", "MemoryStoreObjectCount"],
        ["InMemoryHits", "InMemoryMisses"],
        item,
        section,
    )


check_plugin_jolokia_metrics_in_memory = CheckPlugin(
    name="jolokia_metrics_in_memory",
    service_name="JVM %s In Memory",
    sections=["jolokia_metrics"],
    discovery_function=discover_jolokia_metrics_in_memory,
    check_function=check_jolokia_metrics_in_memory,
)


def discover_jolokia_metrics_on_disk(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=item, parameters=parameters)
        for (item, parameters) in inventory_jolokia_metrics_cache(
            ["OnDiskHitPercentage", "DiskStoreObjectCount", "OnDiskHits", "OnDiskMisses"],
            section,
        )
    ]


def check_jolokia_metrics_on_disk(item: str, section: StringTable) -> CheckResult:
    yield from check_jolokia_metrics_cache(
        ["OnDiskHitPercentage", "DiskStoreObjectCount"],
        ["OnDiskHits", "OnDiskMisses"],
        item,
        section,
    )


check_plugin_jolokia_metrics_on_disk = CheckPlugin(
    name="jolokia_metrics_on_disk",
    service_name="JVM %s On Disk",
    sections=["jolokia_metrics"],
    discovery_function=discover_jolokia_metrics_on_disk,
    check_function=check_jolokia_metrics_on_disk,
)


def discover_jolokia_metrics_off_heap(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=item, parameters=parameters)
        for (item, parameters) in inventory_jolokia_metrics_cache(
            ["OffHeapHitPercentage", "OffHeapStoreObjectCount", "OffHeapHits", "OffHeapMisses"],
            section,
        )
    ]


def check_jolokia_metrics_off_heap(item: str, section: StringTable) -> CheckResult:
    yield from check_jolokia_metrics_cache(
        ["OffHeapHitPercentage", "OffHeapStoreObjectCount"],
        ["OffHeapHits", "OffHeapMisses"],
        item,
        section,
    )


check_plugin_jolokia_metrics_off_heap = CheckPlugin(
    name="jolokia_metrics_off_heap",
    service_name="JVM %s Off Heap",
    sections=["jolokia_metrics"],
    discovery_function=discover_jolokia_metrics_off_heap,
    check_function=check_jolokia_metrics_off_heap,
)


def discover_jolokia_metrics_writer(section: StringTable) -> DiscoveryResult:
    yield from [
        Service(item=item, parameters=parameters)
        for (item, parameters) in inventory_jolokia_metrics_cache(
            ["WriterQueueLength", "WriterMaxQueueSize"], section
        )
    ]


def check_jolokia_metrics_writer(item: str, section: StringTable) -> CheckResult:
    yield from check_jolokia_metrics_cache(
        ["WriterQueueLength", "WriterMaxQueueSize"], [], item, section
    )


check_plugin_jolokia_metrics_writer = CheckPlugin(
    name="jolokia_metrics_writer",
    service_name="JVM %s Cache Writer",
    sections=["jolokia_metrics"],
    discovery_function=discover_jolokia_metrics_writer,
    check_function=check_jolokia_metrics_writer,
)
