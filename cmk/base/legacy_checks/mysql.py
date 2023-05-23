#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="no-untyped-def"

import time

from cmk.base.check_api import (
    check_levels,
    discover,
    get_percent_human_readable,
    get_rate,
    LegacyCheckDefinition,
)
from cmk.base.check_legacy_includes.diskstat import check_diskstat_line
from cmk.base.check_legacy_includes.mysql import mysql_parse_per_item
from cmk.base.config import check_info

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


@mysql_parse_per_item
def parse_mysql(info):
    data = {}
    for line in info:
        try:
            data[line[0]] = int(line[1])
        except IndexError:
            continue
        except ValueError:
            data[line[0]] = line[1]
    return data


def check_mysql_version(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    version = data.get("version")
    if version:
        yield 0, "Version: %s" % version


check_info["mysql"] = LegacyCheckDefinition(
    parse_function=parse_mysql,
    discovery_function=discover(lambda k, values: "version" in values),
    check_function=check_mysql_version,
    service_name="MySQL Version %s",
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
    connects = get_rate("mysql.sessions", time.time(), data["Connections"])

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
    discovery_function=discover(lambda k, values: len(values) > 200),
    check_function=check_mysql_sessions,
    service_name="MySQL Sessions %s",
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


check_info["mysql.innodb_io"] = LegacyCheckDefinition(
    discovery_function=discover(lambda k, values: "Innodb_data_read" in values),
    check_function=check_mysql_iostat,
    service_name="MySQL InnoDB IO %s",
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
        human_readable_func=get_percent_human_readable,
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
        human_readable_func=get_percent_human_readable,
        infoname=status_txt,
    )

    yield check_levels(
        value=conn_threads,
        dsname="connections_conn_threads",
        params=None,
        human_readable_func=lambda x: "",
    )


@discover
def mysql_connections(instance, values):
    return all(
        x in values for x in ["Max_used_connections", "max_connections", "Threads_connected"]
    )


check_info["mysql.connections"] = LegacyCheckDefinition(
    discovery_function=mysql_connections,
    check_function=check_mysql_connections,
    service_name="MySQL Connections %s",
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


def _has_wsrep_provider(data) -> bool:
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
    discovery_function=inventory_mysql_galerasync,
    check_function=check_mysql_galerasync,
    service_name="MySQL Galera Sync %s",
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
    discovery_function=inventory_mysql_galeradonor,
    check_function=check_mysql_galeradonor,
    service_name="MySQL Galera Donor %s",
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
    discovery_function=inventory_mysql_galerastartup,
    check_function=check_mysql_galerastartup,
    service_name="MySQL Galera Startup %s",
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
    discovery_function=inventory_mysql_galerasize,
    check_function=check_mysql_galerasize,
    service_name="MySQL Galera Size %s",
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
    discovery_function=inventory_mysql_galerastatus,
    check_function=check_mysql_galerastatus,
    service_name="MySQL Galera Status %s",
)
