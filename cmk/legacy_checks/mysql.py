#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_average,
    get_rate,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.mysql.agent_based.lib import mysql_parse_per_item

# <<<mysql>>>
# [[mysql]]
# Aborted_clients 0
# Aborted_connects        15
# Binlog_cache_disk_use   0
# Binlog_cache_use        0
# Binlog_stmt_cache_disk_use      0
# Binlog_stmt_cache_use   0
# Bytes_received  7198841
# Bytes_sent      19266624
# Com_admin_commands      200
# Com_assign_to_keycache  0
# Com_alter_db    0
# Com_alter_db_upgrade    0


Section = Mapping[str, Mapping[str, Any]]


@mysql_parse_per_item
def parse_mysql(string_table: Sequence[Sequence[str]]) -> Mapping[str, Any]:  # type: ignore[misc]
    data: dict[str, Any] = {}
    for line in string_table:
        try:
            data[line[0]] = int(line[1])
        except IndexError:
            continue
        except ValueError:
            data[line[0]] = line[1]
    return data


def _discover_keys(keys: set[str]) -> Callable[[Section], DiscoveryResult]:
    def discover(section: Section) -> DiscoveryResult:
        for instance, data in section.items():
            if keys <= set(data):
                yield Service(item=instance)

    return discover


def check_mysql_version(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    if version := data.get("version"):
        yield Result(state=State.OK, summary=f"Version: {version}")


agent_section_mysql = AgentSection(
    name="mysql",
    parse_function=parse_mysql,
)


check_plugin_mysql = CheckPlugin(
    name="mysql",
    service_name="MySQL Version %s",
    discovery_function=_discover_keys({"version"}),
    check_function=check_mysql_version,
)


# .
#   .--Sessions------------------------------------------------------------.
#   |                ____                _                                 |
#   |               / ___|  ___  ___ ___(_) ___  _ __  ___                 |
#   |               \___ \ / _ \/ __/ __| |/ _ \| '_ \/ __|                |
#   |                ___) |  __/\__ \__ \ | (_) | | | \__ \                |
#   |               |____/ \___||___/___/_|\___/|_| |_|___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_mysql_sessions(section: Section) -> DiscoveryResult:
    for instance, data in section.items():
        if len(data) > 200:
            yield Service(item=instance)


# params:
# { "running" : (20, 40),
#    "total" : (100, 400),
#    "connections" : (3, 5 ),
# }


def check_mysql_sessions(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    total_sessions = data["Threads_connected"]
    running_sessions = data["Threads_running"]
    connects = get_rate(
        get_value_store(), "mysql.sessions", time.time(), data["Connections"], raise_overflow=True
    )

    for value, perfvar, what, fmt, unit in [
        (total_sessions, "total_sessions", "total", "%d", ""),
        (running_sessions, "running_sessions", "running", "%d", ""),
        (connects, "connect_rate", "connections", "%.2f", "/s"),
    ]:
        levels = params.get(what)
        infotext = f"{fmt % value} {what}{unit}"
        yield from check_levels_v1(
            value,
            metric_name=perfvar,
            levels_upper=levels,
            label=infotext,
        )


check_plugin_mysql_sessions = CheckPlugin(
    name="mysql_sessions",
    service_name="MySQL Sessions %s",
    sections=["mysql"],
    discovery_function=discover_mysql_sessions,
    check_function=check_mysql_sessions,
    check_ruleset_name="mysql_sessions",
    check_default_parameters={},
)


# .
#   .--InnoDB-IO-----------------------------------------------------------.
#   |           ___                   ____  ____       ___ ___             |
#   |          |_ _|_ __  _ __   ___ |  _ \| __ )     |_ _/ _ \            |
#   |           | || '_ \| '_ \ / _ \| | | |  _ \ _____| | | | |           |
#   |           | || | | | | | | (_) | |_| | |_) |_____| | |_| |           |
#   |          |___|_| |_|_| |_|\___/|____/|____/     |___\___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_mysql_iostat(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    if not ("Innodb_data_read" in data and "Innodb_data_written" in data):
        return

    yield from check_diskstat_line(
        time.time(),
        "innodb_io" + item,
        params,
        read_value=int(data["Innodb_data_read"]),
        write_value=int(data["Innodb_data_written"]),
    )


def check_diskstat_line(
    this_time: float,
    item: str,
    params: Mapping[str, Any],
    read_value: int,
    write_value: int,
) -> CheckResult:
    average_range = params.get("average")
    if average_range == 0:
        average_range = None  # disable averaging when 0 is set

    value_store = get_value_store()

    for metric_name, value in (("read", read_value), ("write", write_value)):
        levels = params.get(f"{metric_name}_bytes")

        bytes_per_sec = get_rate(value_store, metric_name, this_time, value, raise_overflow=True)

        if average_range is not None:
            # yield the un-averaged rate as a metric for reference
            yield Metric(metric_name, bytes_per_sec)
            bytes_per_sec = get_average(
                value_store, f"{metric_name}.avg", this_time, bytes_per_sec, average_range
            )
            check_metric_name = f"{metric_name}.avg"
        else:
            check_metric_name = metric_name

        yield from check_levels_v1(
            bytes_per_sec,
            metric_name=check_metric_name,
            levels_upper=levels,
            render_func=render.iobandwidth,
            label=metric_name.capitalize(),
        )


check_plugin_mysql_innodb_io = CheckPlugin(
    name="mysql_innodb_io",
    service_name="MySQL InnoDB IO %s",
    sections=["mysql"],
    discovery_function=_discover_keys({"Innodb_data_read"}),
    check_function=check_mysql_iostat,
    check_ruleset_name="mysql_innodb_io",
    check_default_parameters={},
)


# .
#   .--Connections---------------------------------------------------------.
#   |        ____                            _   _                         |
#   |       / ___|___  _ __  _ __   ___  ___| |_(_) ___  _ __  ___         |
#   |      | |   / _ \| '_ \| '_ \ / _ \/ __| __| |/ _ \| '_ \/ __|        |
#   |      | |__| (_) | | | | | | |  __/ (__| |_| | (_) | | | \__ \        |
#   |       \____\___/|_| |_|_| |_|\___|\___|\__|_|\___/|_| |_|___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def check_mysql_connections(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return

    if "Max_used_connections" not in data:
        yield Result(state=State.UNKNOWN, summary="Connection information is missing")
        return

    # The maximum number of connections that have been in use simultaneously
    # since the server started.
    conn = float(data["Max_used_connections"])

    # The number of currently open connections
    conn_threads = float(data["Threads_connected"])

    # Maximum number of possible parallel connections, set as a global system variable
    max_conn = float(data["max_connections"])

    perc_used = conn / max_conn * 100
    perc_conn_threads = conn_threads / max_conn * 100

    yield from check_levels_v1(
        perc_used,
        metric_name="connections_perc_used",
        levels_upper=params.get("perc_used"),
        render_func=render.percent,
        label="Max. parallel connections since server start",
    )

    yield Metric("connections_max_used", conn)
    yield Metric("connections_max", max_conn)

    yield from check_levels_v1(
        perc_conn_threads,
        metric_name="connections_perc_conn_threads",
        levels_upper=params.get("perc_conn_threads"),
        render_func=render.percent,
        label="Currently open connections",
    )

    yield Metric("connections_conn_threads", conn_threads)


check_plugin_mysql_connections = CheckPlugin(
    name="mysql_connections",
    service_name="MySQL Connections %s",
    sections=["mysql"],
    discovery_function=_discover_keys(
        {"Max_used_connections", "max_connections", "Threads_connected"}
    ),
    check_function=check_mysql_connections,
    check_ruleset_name="mysql_connections",
    check_default_parameters={},
)


# .
#   .--Galera Sync Status--------------------------------------------------.
#   |         ____       _                  ____                           |
#   |        / ___| __ _| | ___ _ __ __ _  / ___| _   _ _ __   ___         |
#   |       | |  _ / _` | |/ _ \ '__/ _` | \___ \| | | | '_ \ / __|        |
#   |       | |_| | (_| | |  __/ | | (_| |  ___) | |_| | | | | (__         |
#   |        \____|\__,_|_|\___|_|  \__,_| |____/ \__, |_| |_|\___|        |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


def _has_wsrep_provider(data: Mapping[str, object]) -> bool:
    return data.get("wsrep_provider") not in (None, "none")


def discover_mysql_galerasync(section: Section) -> DiscoveryResult:
    for instance, data in section.items():
        if _has_wsrep_provider(data) and "wsrep_local_state_comment" in data:
            yield Service(item=instance)


def check_mysql_galerasync(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    wsrep_local_state_comment = data.get("wsrep_local_state_comment")
    if wsrep_local_state_comment is None:
        return

    state = State.OK if wsrep_local_state_comment == "Synced" else State.CRIT
    yield Result(state=state, summary=f"WSREP local state comment: {wsrep_local_state_comment}")


check_plugin_mysql_galerasync = CheckPlugin(
    name="mysql_galerasync",
    service_name="MySQL Galera Sync %s",
    sections=["mysql"],
    discovery_function=discover_mysql_galerasync,
    check_function=check_mysql_galerasync,
)


# .
#   .--Galera Donor--------------------------------------------------------.
#   |      ____       _                  ____                              |
#   |     / ___| __ _| | ___ _ __ __ _  |  _ \  ___  _ __   ___  _ __      |
#   |    | |  _ / _` | |/ _ \ '__/ _` | | | | |/ _ \| '_ \ / _ \| '__|     |
#   |    | |_| | (_| | |  __/ | | (_| | | |_| | (_) | | | | (_) | |        |
#   |     \____|\__,_|_|\___|_|  \__,_| |____/ \___/|_| |_|\___/|_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_mysql_galeradonor(section: Section) -> DiscoveryResult:
    for instance, data in section.items():
        if _has_wsrep_provider(data) and "wsrep_sst_donor" in data:
            yield Service(item=instance, parameters={"wsrep_sst_donor": data["wsrep_sst_donor"]})


def check_mysql_galeradonor(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    wsrep_sst_donor = data.get("wsrep_sst_donor")
    if wsrep_sst_donor is None:
        return

    state = State.OK
    infotext = f"WSREP SST donor: {wsrep_sst_donor}"

    p_wsrep_sst_donor = params["wsrep_sst_donor"]
    if wsrep_sst_donor != p_wsrep_sst_donor:
        state = State.WARN
        infotext += f" (at discovery: {p_wsrep_sst_donor})"

    yield Result(state=state, summary=infotext)


check_plugin_mysql_galeradonor = CheckPlugin(
    name="mysql_galeradonor",
    service_name="MySQL Galera Donor %s",
    sections=["mysql"],
    discovery_function=discover_mysql_galeradonor,
    check_function=check_mysql_galeradonor,
    check_default_parameters={},
)


# .
#   .--Galera Startup------------------------------------------------------.
#   |  ____       _                  ____  _             _                 |
#   | / ___| __ _| | ___ _ __ __ _  / ___|| |_ __ _ _ __| |_ _   _ _ __    |
#   || |  _ / _` | |/ _ \ '__/ _` | \___ \| __/ _` | '__| __| | | | '_ \   |
#   || |_| | (_| | |  __/ | | (_| |  ___) | || (_| | |  | |_| |_| | |_) |  |
#   | \____|\__,_|_|\___|_|  \__,_| |____/ \__\__,_|_|   \__|\__,_| .__/   |
#   |                                                             |_|      |
#   '----------------------------------------------------------------------'


def discover_mysql_galerastartup(section: Section) -> DiscoveryResult:
    for instance, data in section.items():
        if _has_wsrep_provider(data) and "wsrep_cluster_address" in data:
            yield Service(item=instance)


def check_mysql_galerastartup(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    wsrep_cluster_address = data.get("wsrep_cluster_address")
    if wsrep_cluster_address is None:
        return

    if wsrep_cluster_address == "gcomm://":
        yield Result(state=State.CRIT, summary="WSREP cluster address is empty")
    else:
        yield Result(state=State.OK, summary=f"WSREP cluster address: {wsrep_cluster_address}")


check_plugin_mysql_galerastartup = CheckPlugin(
    name="mysql_galerastartup",
    service_name="MySQL Galera Startup %s",
    sections=["mysql"],
    discovery_function=discover_mysql_galerastartup,
    check_function=check_mysql_galerastartup,
)


# .
#   .--Galera Cluster Size-------------------------------------------------.
#   |     ____       _                   ____ _           _                |
#   |    / ___| __ _| | ___ _ __ __ _   / ___| |_   _ ___| |_ ___ _ __     |
#   |   | |  _ / _` | |/ _ \ '__/ _` | | |   | | | | / __| __/ _ \ '__|    |
#   |   | |_| | (_| | |  __/ | | (_| | | |___| | |_| \__ \ ||  __/ |       |
#   |    \____|\__,_|_|\___|_|  \__,_|  \____|_|\__,_|___/\__\___|_|       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_mysql_galerasize(section: Section) -> DiscoveryResult:
    for instance, data in section.items():
        if _has_wsrep_provider(data) and "wsrep_cluster_size" in data:
            yield Service(item=instance, parameters={"invsize": data["wsrep_cluster_size"]})


def check_mysql_galerasize(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    wsrep_cluster_size = data.get("wsrep_cluster_size")
    if wsrep_cluster_size is None:
        return

    state = State.OK
    infotext = f"WSREP cluster size: {wsrep_cluster_size}"

    p_wsrep_cluster_size = params["invsize"]
    if wsrep_cluster_size != p_wsrep_cluster_size:
        state = State.CRIT
        infotext += f" (at discovery: {p_wsrep_cluster_size})"

    yield Result(state=state, summary=infotext)


check_plugin_mysql_galerasize = CheckPlugin(
    name="mysql_galerasize",
    service_name="MySQL Galera Size %s",
    sections=["mysql"],
    discovery_function=discover_mysql_galerasize,
    check_function=check_mysql_galerasize,
    check_default_parameters={},
)


# .
#   .--Galera Status-------------------------------------------------------.
#   |      ____       _                  ____  _        _                  |
#   |     / ___| __ _| | ___ _ __ __ _  / ___|| |_ __ _| |_ _   _ ___      |
#   |    | |  _ / _` | |/ _ \ '__/ _` | \___ \| __/ _` | __| | | / __|     |
#   |    | |_| | (_| | |  __/ | | (_| |  ___) | || (_| | |_| |_| \__ \     |
#   |     \____|\__,_|_|\___|_|  \__,_| |____/ \__\__,_|\__|\__,_|___/     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_mysql_galerastatus(section: Section) -> DiscoveryResult:
    for instance, data in section.items():
        if _has_wsrep_provider(data) and "wsrep_cluster_status" in data:
            yield Service(item=instance)


def check_mysql_galerastatus(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    wsrep_cluster_status = data.get("wsrep_cluster_status")
    if wsrep_cluster_status is None:
        return

    state = State.OK if wsrep_cluster_status == "Primary" else State.CRIT
    yield Result(state=state, summary=f"WSREP cluster status: {wsrep_cluster_status}")


check_plugin_mysql_galerastatus = CheckPlugin(
    name="mysql_galerastatus",
    service_name="MySQL Galera Status %s",
    sections=["mysql"],
    discovery_function=discover_mysql_galerastatus,
    check_function=check_mysql_galerastatus,
)
