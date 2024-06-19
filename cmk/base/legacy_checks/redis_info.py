#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.redis import parse_redis_info
from cmk.base.check_legacy_includes.uptime import check_uptime_seconds
from cmk.base.config import check_info

from cmk.agent_based.v2 import render

# <<<redis_info>>>
# [[[MY_FIRST_REDIS|127.0.0.1|6380]]]
# ...

#   .--Server--------------------------------------------------------------.
#   |                   ____                                               |
#   |                  / ___|  ___ _ ____   _____ _ __                     |
#   |                  \___ \ / _ \ '__\ \ / / _ \ '__|                    |
#   |                   ___) |  __/ |   \ V /  __/ |                       |
#   |                  |____/ \___|_|    \_/ \___|_|                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# ...
# Server
# redis_version:4.0.9
# redis_git_sha1:00000000
# redis_git_dirty:0
# redis_build_id:9435c3c2879311f3
# redis_mode:standalone
# os:Linux 4.15.0-1065-oem x86_64
# arch_bits:64
# multiplexing_api:epoll
# atomicvar_api:atomic-builtin
# gcc_version:7.4.0
# process_id:1029
# run_id:27bb4e37e85094b590b4693d6c6e11d07cd6400a
# tcp_port:6380
# uptime_in_seconds:29349
# uptime_in_days:0
# hz:10
# lru_clock:15193378
# executable:/usr/bin/redis-server
# config_file:/etc/redis/redis2.conf
#
# Description of possible output:
# redis_version: Version of the Redis server
# redis_git_sha1: Git SHA1
# redis_git_dirty: Git dirty flag
# redis_build_id: The build id
# redis_mode: The server's mode ("standalone", "sentinel" or "cluster")
# os: Operating system hosting the Redis server
# arch_bits: Architecture (32 or 64 bits)
# multiplexing_api: Event loop mechanism used by Redis
# atomicvar_api: Atomicvar API used by Redis
# gcc_version: Version of the GCC compiler used to compile the Redis server
# process_id: PID of the server process
# run_id: Random value identifying the Redis server (to be used by Sentinel and Cluster)
# tcp_port: TCP/IP listen port
# uptime_in_seconds: Number of seconds since Redis server start
# uptime_in_days: Same value expressed in days
# hz: The server's frequency setting
# lru_clock: Clock incrementing every minute, for LRU management
# executable: The path to the server's executable
# config_file: The path to the config file


def discover_redis_info(section):
    yield from ((item, {}) for item in section)


def check_redis_info(item, params, parsed):
    if not (item_data := parsed.get(item)):
        return
    server_data = item_data.get("Server")
    if server_data is None:
        return

    server_mode = server_data.get("redis_mode")
    if server_mode is not None:
        mode_state = 0
        infotext = "Mode: %s" % server_mode.title()
        mode_params = params.get("expected_mode")
        if mode_params is not None:
            if mode_params != server_mode:
                mode_state = 1
                infotext += " (expected: %s)" % mode_params.title()

        yield mode_state, infotext

    server_uptime = server_data.get("uptime_in_seconds")
    if server_uptime is not None:
        yield check_uptime_seconds(params, server_uptime)

    for key, infotext in [
        ("redis_version", "Version"),
        ("gcc_version", "GCC compiler version"),
        ("process_id", "PID"),
    ]:
        value = server_data.get(key)
        if value is not None:
            yield 0, f"{infotext}: {value}"

    host_data = item_data.get("host")
    if host_data is not None:
        addr = "Socket" if item_data.get("port") == "unix-socket" else "IP"
        yield 0, f"{addr}: {host_data}"

    port_data = item_data.get("port")
    if port_data is not None and port_data != "unix-socket":
        yield 0, "Port: %s" % port_data


check_info["redis_info"] = LegacyCheckDefinition(
    parse_function=parse_redis_info,
    service_name="Redis %s Server Info",
    discovery_function=discover_redis_info,
    check_function=check_redis_info,
    check_ruleset_name="redis_info",
)
# .
#   .--Persistence---------------------------------------------------------.
#   |           ____               _     _                                 |
#   |          |  _ \ ___ _ __ ___(_)___| |_ ___ _ __   ___ ___            |
#   |          | |_) / _ \ '__/ __| / __| __/ _ \ '_ \ / __/ _ \           |
#   |          |  __/  __/ |  \__ \ \__ \ ||  __/ | | | (_|  __/           |
#   |          |_|   \___|_|  |___/_|___/\__\___|_| |_|\___\___|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# ...
# Persistence
# loading:0
# rdb_changes_since_last_save:0
# rdb_bgsave_in_progress:0
# rdb_last_save_time:1578466632
# rdb_last_bgsave_status:ok
# rdb_last_bgsave_time_sec:-1
# rdb_current_bgsave_time_sec:-1
# rdb_last_cow_size:0
# aof_enabled:0
# aof_rewrite_in_progress:0
# aof_rewrite_scheduled:0
# aof_last_rewrite_time_sec:-1
# aof_current_rewrite_time_sec:-1
# aof_last_bgrewrite_status:ok
# aof_last_write_status:ok
# aof_last_cow_size:0

# Description of possible output:
# loading - Flag indicating if the load of a dump file is on-going
# rdb_changes_since_last_save - Number of changes since the last dump
# rdb_bgsave_in_progress - Flag indicating a RDB save is on-going
# rdb_last_save_time - Epoch-based timestamp of last successful RDB save
# rdb_last_bgsave_status - Status of last RDB save operation
# rdb_last_bgsave_time_sec - Duration of the last RDB save operation in seconds
# rdb_current_bgsave_time_sec - Duration of the on-going RDB save operation if any
# rdb_last_cow_size - size in bytes of copy-on-write allocations during last RDB save operation
# aof_enabled - Flag indicating AOF logging is activated
# aof_rewrite_in_progress - Flag indicating a AOF rewrite operation is on-going
# aof_rewrite_scheduled - Flag indicating an AOF rewrite operation will be scheduled once the on-going RDB save is complete.
# aof_last_rewrite_time_sec - Duration of last AOF rewrite operation in seconds
# aof_current_rewrite_time_sec - Duration of the on-going AOF rewrite operation if any
# aof_last_bgrewrite_status - Status of last AOF rewrite operation
# aof_last_write_status - Status of the last write operation to the AOF
# aof_last_cow_size - The size in bytes of copy-on-write allocations during the last AOF rewrite operation


def discover_redis_info_persistence(section):
    yield from ((item, {}) for item, data in section.items() if "Persistence" in data)


def check_redis_info_persistence(item, params, item_data):
    persistence_data = item_data.get(item, {}).get("Persistence")
    if not persistence_data or persistence_data is None:
        return

    for status, duration, infotext in [
        ("rdb_last_bgsave_status", "rdb_last_bgsave", "Last RDB save operation: "),
        ("aof_last_bgrewrite_status", "aof_last_rewrite", "Last AOF rewrite operation: "),
    ]:
        value = persistence_data.get(status)
        if value is not None:
            state = 0
            if value != "ok":
                state = params["%s_state" % duration]
                infotext += "faulty"
            else:
                infotext += "successful"

            duration_val = persistence_data.get("%s_time_sec" % duration)
            if duration_val is not None and duration_val != -1:
                infotext += " (Duration: %s)" % render.timespan(duration_val)
            yield state, infotext

    rdb_save_time = persistence_data.get("rdb_last_save_time")
    if rdb_save_time is not None:
        yield 0, "Last successful RDB save: %s" % render.datetime(rdb_save_time)

    rdb_changes = persistence_data.get("rdb_changes_since_last_save")
    if rdb_changes is not None:
        yield check_levels(
            rdb_changes,
            "changes_sld",
            params.get("rdb_changes_count"),
            human_readable_func=int,
            infoname="Number of changes since last dump",
        )


check_info["redis_info.persistence"] = LegacyCheckDefinition(
    service_name="Redis %s Persistence",
    sections=["redis_info"],
    discovery_function=discover_redis_info_persistence,
    check_function=check_redis_info_persistence,
    check_ruleset_name="redis_info_persistence",
    check_default_parameters={
        "rdb_last_bgsave_state": 1,
        "aof_last_rewrite_state": 1,
    },
)
# .
#   .--Clients-------------------------------------------------------------.
#   |                     ____ _ _            _                            |
#   |                    / ___| (_) ___ _ __ | |_ ___                      |
#   |                   | |   | | |/ _ \ '_ \| __/ __|                     |
#   |                   | |___| | |  __/ | | | |_\__ \                     |
#   |                    \____|_|_|\___|_| |_|\__|___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# ...
# Clients
# connected_clients:1
# client_longest_output_list:0
# client_biggest_input_buf:0
# blocked_clients:0

# Description of possible output:
# connected_clients - Number of client connections (excluding connections from replicas)
# client_longest_output_list - longest output list among current client connections
# client_biggest_input_buf - biggest input buffer among current client connections
# blocked_clients - Number of clients pending on a blocking call (BLPOP, BRPOP, BRPOPLPUSH)


def discover_redis_info_clients(section):
    yield from ((item, {}) for item, data in section.items() if "Clients" in data)


def check_redis_info_clients(item, params, item_data):
    clients_data = item_data.get(item, {}).get("Clients")
    if not clients_data or clients_data is None:
        return

    for data_key, param_key, infotext in [
        ("connected_clients", "connected", "Number of client connections"),
        ("client_longest_output_list", "output", "Longest output list"),
        ("client_biggest_input_buf", "input", "Biggest input buffer"),
        ("blocked_clients", "blocked", "Number of clients pending on a blocking call"),
    ]:
        clients_value = clients_data.get(data_key)
        if clients_value is None:
            continue

        upper_level = params.get("%s_upper" % param_key, (None, None))
        lower_level = params.get("%s_lower" % param_key, (None, None))

        yield check_levels(
            clients_value,
            "clients_%s" % param_key,
            upper_level + lower_level,
            human_readable_func=int,
            infoname=infotext,
        )


check_info["redis_info.clients"] = LegacyCheckDefinition(
    service_name="Redis %s Clients",
    sections=["redis_info"],
    discovery_function=discover_redis_info_clients,
    check_function=check_redis_info_clients,
    check_ruleset_name="redis_info_clients",
)
# .
