#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Result, Service, State
from cmk.plugins.lib.uptime import check as check_uptime_seconds
from cmk.plugins.lib.uptime import Section as UptimeSection
from cmk.plugins.redis.agent_based.redis_base import Section

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


def discover_redis_info(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_redis_info(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (item_data := section.get(item)):
        return

    if (error := item_data.get("error")) is not None:
        yield Result(state=State.CRIT, summary=f"Error: {error}")

    server_data = item_data.get("Server")
    if server_data is None:
        return

    server_mode = server_data.get("redis_mode")
    if server_mode is not None:
        mode_state = State.OK
        infotext = "Mode: %s" % server_mode.title()
        mode_params = params.get("expected_mode")
        if mode_params is not None:
            if mode_params != server_mode:
                mode_state = State.WARN
                infotext += " (expected: %s)" % mode_params.title()

        yield Result(state=mode_state, summary=infotext)

    server_uptime = server_data.get("uptime_in_seconds")
    if server_uptime is not None:
        yield from check_uptime_seconds(
            params, UptimeSection(uptime_sec=server_uptime, message=None)
        )

    for key, infotext in [
        ("redis_version", "Version"),
        ("gcc_version", "GCC compiler version"),
        ("process_id", "PID"),
    ]:
        value = server_data.get(key)
        if value is not None:
            yield Result(state=State.OK, summary=f"{infotext}: {value}")

    host_data = item_data.get("host")
    if host_data is not None:
        addr = "Socket" if item_data.get("port") == "unix-socket" else "IP"
        yield Result(state=State.OK, summary=f"{addr}: {host_data}")

    port_data = item_data.get("port")
    if port_data is not None and port_data != "unix-socket":
        yield Result(state=State.OK, summary="Port: %s" % port_data)


check_plugin_redis_info = CheckPlugin(
    name="redis_info",
    service_name="Redis %s Server Info",
    discovery_function=discover_redis_info,
    check_function=check_redis_info,
    check_ruleset_name="redis_info",
    check_default_parameters={},
)
