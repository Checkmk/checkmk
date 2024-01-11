#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Iterable, Mapping, MutableSequence, Sequence
from typing import Any, Protocol

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.mysql import mysql_parse_per_item
from cmk.base.config import check_info

from cmk.agent_based.v2 import get_average, get_rate, get_value_store, render

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

#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


Section = Mapping[str, Mapping[str, Any]]

Service = tuple[str, dict]


class DiscoveryFunction(Protocol):
    def __call__(self, section: Section) -> Iterable[Service]:
        ...


@mysql_parse_per_item
def parse_mysql(string_table):
    data = {}
    for line in string_table:
        try:
            data[line[0]] = int(line[1])
        except IndexError:
            continue
        except ValueError:
            data[line[0]] = line[1]
    return data


def _discover_keys(keys: set[str]) -> DiscoveryFunction:
    def discover(section: Section) -> Iterable[Service]:
        yield from ((instance, {}) for instance, data in section.items() if keys <= set(data))

    return discover


def check_mysql_version(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    version = data.get("version")
    if version:
        yield 0, "Version: %s" % version


check_info["mysql"] = LegacyCheckDefinition(
    parse_function=parse_mysql,
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


def discover_mysql_sessions(section: Section) -> Iterable[Service]:
    yield from ((instance, {}) for instance, data in section.items() if len(data) > 200)


# params:
# { "running" : (20, 40),
#    "total" : (100, 400),
#    "connections" : (3, 5 ),
# }


def check_mysql_sessions(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    total_sessions = data["Threads_connected"]
    running_sessions = data["Threads_running"]
    connects = get_rate(
        get_value_store(), "mysql.sessions", time.time(), data["Connections"], raise_overflow=True
    )

    for value, perfvar, what, format_str, unit in [
        (total_sessions, "total_sessions", "total", "%d %s%s", ""),
        (running_sessions, "running_sessions", "running", "%d %s%s", ""),
        (connects, "connect_rate", "connections", "%.2f %s%s", "/s"),
    ]:
        infotext = format_str % (value, what, unit)
        status = 0
        if what in params:
            warn, crit = params[what]
            if value >= crit:
                status = 2
                infotext += "(!!)"
            elif value >= warn:
                status = 1
                infotext += "(!)"
        else:
            warn, crit = None, None

        yield status, infotext, [(perfvar, value, warn, crit)]


check_info["mysql.sessions"] = LegacyCheckDefinition(
    service_name="MySQL Sessions %s",
    sections=["mysql"],
    discovery_function=discover_mysql_sessions,
    check_function=check_mysql_sessions,
    check_ruleset_name="mysql_sessions",
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


def check_mysql_iostat(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    if not ("Innodb_data_read" in data and "Innodb_data_written" in data):
        return

    line = [None, None, data["Innodb_data_read"] // 512, data["Innodb_data_written"] // 512]
    yield check_diskstat_line(time.time(), "innodb_io" + item, params, line)


def check_diskstat_line(  # pylint: disable=too-many-branches
    this_time: float,
    item: str,
    params: Mapping[str, Any],
    line: Sequence[Any],
    mode: str = "sectors",
) -> tuple[int, str, MutableSequence[Any],]:
    average_range = params.get("average")
    if average_range == 0:
        average_range = None  # disable averaging when 0 is set

    value_store = get_value_store()

    perfdata: MutableSequence[Any] = []
    infos: MutableSequence[str] = []
    status: int = 0
    node = line[0]
    if node is not None and node != "":
        infos.append("Node %s" % node)

    for what, ctr in [("read", line[2]), ("write", line[3])]:
        if node:
            countername = f"diskstat.{node}.{item}.{what}"
        else:
            countername = f"diskstat.{item}.{what}"

        # unpack levels now, need also for perfdata
        levels = params.get(what)
        if isinstance(levels, tuple):
            warn, crit = levels
        else:
            warn, crit = None, None

        per_sec = get_rate(get_value_store(), countername, this_time, int(ctr), raise_overflow=True)
        if mode == "sectors":
            # compute IO rate in bytes/sec
            bytes_per_sec = per_sec * 512
        elif mode == "bytes":
            bytes_per_sec = per_sec

        dsname = what

        # compute average of the rate over ___ minutes
        if average_range is not None:
            perfdata.append((dsname, bytes_per_sec, warn, crit))
            bytes_per_sec = get_average(
                value_store, f"{countername}.avg", this_time, bytes_per_sec, average_range
            )
            dsname += ".avg"

        # check levels
        state, text, extraperf = check_levels(
            bytes_per_sec,
            dsname,
            levels,
            scale=1024**2,
            statemarkers=True,
            human_readable_func=render.iobandwidth,
            infoname=what,
        )
        if text:
            infos.append(text)
        status = max(state, status)
        perfdata += extraperf

    # Add performance data for averaged IO
    if average_range is not None:
        perfdata = [perfdata[0], perfdata[2], perfdata[1], perfdata[3]]

    # Process IOs when available
    ios_per_sec = None
    if len(line) >= 6 and line[4] >= 0 and line[5] > 0:
        reads, writes = map(int, line[4:6])
        if "read_ios" in params:
            warn, crit = params["read_ios"]
            if reads >= crit:
                infos.append("Read operations: %d (!!)" % (reads))
                status = 2
            elif reads >= warn:
                infos.append("Read operations: %d (!)" % (reads))
                status = max(status, 1)
        else:
            warn, crit = None, None
        if "write_ios" in params:
            warn, crit = params["write_ios"]
            if writes >= crit:
                infos.append("Write operations: %d (!!)" % (writes))
                status = 2
            elif writes >= warn:
                infos.append("Write operations: %d (!)" % (writes))
                status = max(status, 1)
        else:
            warn, crit = None, None
        ios = reads + writes
        ios_per_sec = get_rate(
            get_value_store(), countername + ".ios", this_time, ios, raise_overflow=True
        )
        infos.append("IOs: %.2f/sec" % ios_per_sec)

        if params.get("latency_perfdata"):
            perfdata.append(("ios", ios_per_sec))

    # Do Latency computation if this information is available:
    if len(line) >= 7 and line[6] >= 0:
        timems = int(line[6])
        timems_per_sec = get_rate(
            get_value_store(), countername + ".time", this_time, timems, raise_overflow=True
        )
        if not ios_per_sec:
            latency = 0.0
        else:
            latency = timems_per_sec / ios_per_sec  # fixed: true-division
        infos.append("Latency: %.2fms" % latency)
        if "latency" in params:
            warn, crit = params["latency"]
            if latency >= crit:
                status = 2
                infos[-1] += "(!!)"
            elif latency >= warn:
                status = max(status, 1)
                infos[-1] += "(!)"
        else:
            warn, crit = None, None

        if params.get("latency_perfdata"):
            perfdata.append(("latency", latency, warn, crit))

    # Queue Lengths (currently only Windows). Windows uses counters here.
    # I have not understood, why....
    if len(line) >= 9:
        for what, ctr in [("read", line[7]), ("write", line[8])]:
            countername = f"diskstat.{item}.ql.{what}"
            levels = params.get(what + "_ql")
            if levels:
                warn, crit = levels
            else:
                warn, crit = None, None

            qlx = get_rate(get_value_store(), countername, this_time, int(ctr), raise_overflow=True)
            ql = qlx / 10000000.0
            infos.append(what.title() + " Queue: %.2f" % ql)

            # check levels
            if levels is not None:
                if ql >= crit:
                    status = 2
                    infos[-1] += "(!!)"
                elif ql >= warn:
                    status = max(status, 1)
                    infos[-1] += "(!)"

            if params.get("ql_perfdata"):
                perfdata.append((what + "_ql", ql))

    return (status, ", ".join(infos), perfdata)


check_info["mysql.innodb_io"] = LegacyCheckDefinition(
    service_name="MySQL InnoDB IO %s",
    sections=["mysql"],
    discovery_function=_discover_keys({"Innodb_data_read"}),
    check_function=check_mysql_iostat,
    check_ruleset_name="mysql_innodb_io",
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


def check_mysql_connections(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    if "Max_used_connections" not in data:
        yield 3, "Connection information is missing"
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

    status_txt = "Max. parallel connections since server start"
    yield check_levels(
        value=perc_used,
        dsname="connections_perc_used",
        params=params.get("perc_used"),
        human_readable_func=render.percent,
        infoname=status_txt,
    )

    yield check_levels(
        value=conn,
        dsname="connections_max_used",
        params=None,
        human_readable_func=lambda x: "",
    )

    yield check_levels(
        value=max_conn,
        dsname="connections_max",
        params=None,
        human_readable_func=lambda x: "",
    )

    status_txt = "Currently open connections"
    yield check_levels(
        value=perc_conn_threads,
        dsname="connections_perc_conn_threads",
        params=params.get("perc_conn_threads"),
        human_readable_func=render.percent,
        infoname=status_txt,
    )

    yield check_levels(
        value=conn_threads,
        dsname="connections_conn_threads",
        params=None,
        human_readable_func=lambda x: "",
    )


check_info["mysql.connections"] = LegacyCheckDefinition(
    service_name="MySQL Connections %s",
    sections=["mysql"],
    discovery_function=_discover_keys(
        {"Max_used_connections", "max_connections", "Threads_connected"}
    ),
    check_function=check_mysql_connections,
    check_ruleset_name="mysql_connections",
)

# .
#   .--Galera Sync Status--------------------------------------------------.
#   |         ____       _                  ____                           |
#   |        / ___| __ _| | ___ _ __ __ _  / ___| _   _ _ __   ___         |
#   |       | |  _ / _` | |/ _ \ '__/ _` | \___ \| | | | '_ \ / __|        |
#   |       | |_| | (_| | |  __/ | | (_| |  ___) | |_| | | | | (__         |
#   |        \____|\__,_|_|\___|_|  \__,_| |____/ \__, |_| |_|\___|        |
#   |                                             |___/                    |
#   |                    ____  _        _                                  |
#   |                   / ___|| |_ __ _| |_ _   _ ___                      |
#   |                   \___ \| __/ _` | __| | | / __|                     |
#   |                    ___) | || (_| | |_| |_| \__ \                     |
#   |                   |____/ \__\__,_|\__|\__,_|___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def _has_wsrep_provider(data: Mapping[str, object]) -> bool:
    return data.get("wsrep_provider") not in (None, "none")


def inventory_mysql_galerasync(parsed):
    for instance, data in parsed.items():
        if _has_wsrep_provider(data) and "wsrep_local_state_comment" in data:
            yield instance, {}


def check_mysql_galerasync(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    wsrep_local_state_comment = data.get("wsrep_local_state_comment")
    if wsrep_local_state_comment is None:
        return

    if wsrep_local_state_comment == "Synced":
        state = 0
    else:
        state = 2
    yield state, "WSREP local state comment: %s" % wsrep_local_state_comment


check_info["mysql.galerasync"] = LegacyCheckDefinition(
    service_name="MySQL Galera Sync %s",
    sections=["mysql"],
    discovery_function=inventory_mysql_galerasync,
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
#   +----------------------------------------------------------------------+


def inventory_mysql_galeradonor(parsed):
    for instance, data in parsed.items():
        if _has_wsrep_provider(data) and "wsrep_sst_donor" in data:
            yield instance, {"wsrep_sst_donor": data["wsrep_sst_donor"]}


def check_mysql_galeradonor(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    wsrep_sst_donor = data.get("wsrep_sst_donor")
    if wsrep_sst_donor is None:
        return

    state = 0
    infotext = "WSREP SST donor: %s" % wsrep_sst_donor

    p_wsrep_sst_donor = params["wsrep_sst_donor"]
    if wsrep_sst_donor != p_wsrep_sst_donor:
        state = 1
        infotext += " (at discovery: %s)" % p_wsrep_sst_donor

    yield state, infotext


check_info["mysql.galeradonor"] = LegacyCheckDefinition(
    service_name="MySQL Galera Donor %s",
    sections=["mysql"],
    discovery_function=inventory_mysql_galeradonor,
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
#   +----------------------------------------------------------------------+


def inventory_mysql_galerastartup(parsed):
    for instance, data in parsed.items():
        if _has_wsrep_provider(data) and "wsrep_cluster_address" in data:
            yield instance, {}


def check_mysql_galerastartup(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    wsrep_cluster_address = data.get("wsrep_cluster_address")
    if wsrep_cluster_address is None:
        return

    if wsrep_cluster_address == "gcomm://":
        yield 2, "WSREP cluster address is empty"
    else:
        yield 0, "WSREP cluster address: %s" % wsrep_cluster_address


check_info["mysql.galerastartup"] = LegacyCheckDefinition(
    service_name="MySQL Galera Startup %s",
    sections=["mysql"],
    discovery_function=inventory_mysql_galerastartup,
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
#   |                           ____  _                                    |
#   |                          / ___|(_)_______                            |
#   |                          \___ \| |_  / _ \                           |
#   |                           ___) | |/ /  __/                           |
#   |                          |____/|_/___\___|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def inventory_mysql_galerasize(parsed):
    for instance, data in parsed.items():
        if _has_wsrep_provider(data) and "wsrep_cluster_size" in data:
            yield instance, {"invsize": data["wsrep_cluster_size"]}


def check_mysql_galerasize(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    wsrep_cluster_size = data.get("wsrep_cluster_size")
    if wsrep_cluster_size is None:
        return

    state = 0
    infotext = "WSREP cluster size: %s" % wsrep_cluster_size

    p_wsrep_cluster_size = params["invsize"]
    if wsrep_cluster_size != p_wsrep_cluster_size:
        state = 2
        infotext += " (at discovery: %s)" % p_wsrep_cluster_size

    yield state, infotext


check_info["mysql.galerasize"] = LegacyCheckDefinition(
    service_name="MySQL Galera Size %s",
    sections=["mysql"],
    discovery_function=inventory_mysql_galerasize,
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
#   +----------------------------------------------------------------------+


def inventory_mysql_galerastatus(parsed):
    for instance, data in parsed.items():
        if _has_wsrep_provider(data) and "wsrep_cluster_status" in data:
            yield instance, {}


def check_mysql_galerastatus(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    wsrep_cluster_status = data.get("wsrep_cluster_status")
    if wsrep_cluster_status is None:
        return

    if wsrep_cluster_status == "Primary":
        state = 0
    else:
        state = 2
    yield state, "WSREP cluster status: %s" % wsrep_cluster_status


check_info["mysql.galerastatus"] = LegacyCheckDefinition(
    service_name="MySQL Galera Status %s",
    sections=["mysql"],
    discovery_function=inventory_mysql_galerastatus,
    check_function=check_mysql_galerastatus,
)
