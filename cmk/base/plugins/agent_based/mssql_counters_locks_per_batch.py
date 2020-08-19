#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
def inventory_mssql_counters_locks_per_batch(parsed):
    db_names = [(obj.split(":")[0], node_name)
                for node_name, node_data in parsed.items()
                for (obj, _instance) in node_data
                if ":" in obj]

    for db_name, node_name in db_names:
        node_data = parsed[node_name]
        if "lock_requests/sec" not in node_data.get(("%s:Locks" % db_name, "_Total"), {}):
            continue
        if "batch_requests/sec" not in node_data.get(("%s:SQL_Statistics" % db_name, "None"), {}):
            continue
        yield db_name, {}


def check_mssql_counters_locks_per_batch(item, params, parsed):
    locks_key = ("%s:Locks" % item, "_Total")
    data_locks_data = {
        node_name: node_data[locks_key]
        for node_name, node_data in parsed.items()
        if locks_key in node_data
    }
    stats_key = ("%s:SQL_Statistics" % item, "None")
    data_stats_data = {
        node_name: node_data[stats_key]
        for node_name, node_data in parsed.items()
        if stats_key in node_data
    }

    if not any(list(data_locks_data.values()) + list(data_stats_data.values())):
        # Assume general connection problem to the database, which is reported
        # by the "X Instance" service and skip this check.
        raise MKCounterWrapped("Failed to connect to database")

    for node_name in set(list(data_locks_data) + list(data_stats_data)):
        data_locks = data_locks_data[node_name]
        data_stats = data_stats_data[node_name]
        now = data_locks.get('utc_time', data_stats.get('utc_time'))
        if now is None:
            now = time.time()

        locks = data_locks["lock_requests/sec"]
        batches = data_stats["batch_requests/sec"]

        lock_rate = get_rate("mssql_counters_locks_per_batch.%s.%s.locks" % (node_name, item), now,
                             locks)
        batch_rate = get_rate("mssql_counters_locks_per_batch.%s.%s.batches" % (node_name, item),
                              now, batches)

        if batch_rate == 0:
            lock_per_batch = 0
        else:
            lock_per_batch = lock_rate / batch_rate  # fixed: true-division

        node_info = ""
        if node_name:
            node_info = "[%s] " % node_name
        infotext = "%s%.1f" % (node_info, lock_per_batch)
        state = 0

        warn, crit = params.get('locks_per_batch', (None, None))
        if crit is not None and lock_per_batch >= crit:
            state = 2
        elif warn is not None and lock_per_batch >= warn:
            state = 1

        if state:
            infotext += " (warn/crit at %.1f/%.1f per second)" % (warn, crit)

        yield state, infotext, [("locks_per_batch", lock_per_batch, warn, crit)]


check_info["mssql_counters.locks_per_batch"] = {
    "inventory_function": inventory_mssql_counters_locks_per_batch,
    "check_function": check_mssql_counters_locks_per_batch,
    "service_description": "MSSQL %s Locks per Batch",
    "has_perfdata": True,
    "group": "mssql_stats",
    'node_info': True,
}
"""
