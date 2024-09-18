#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import (
    check_levels as check_levels_v1,  # we can only use v2 after migrating the ruleset!
)
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.redis.agent_based.redis_base import Section

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


def discover_redis_info_persistence(section: Any) -> DiscoveryResult:
    yield from (Service(item=item) for item, data in section.items() if "Persistence" in data)


def check_redis_info_persistence(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    persistence_data = section.get(item, {}).get("Persistence")
    if not persistence_data or persistence_data is None:
        return

    for status, duration, infotext in [
        ("rdb_last_bgsave_status", "rdb_last_bgsave", "Last RDB save operation: "),
        ("aof_last_bgrewrite_status", "aof_last_rewrite", "Last AOF rewrite operation: "),
    ]:
        value = persistence_data.get(status)
        if value is not None:
            state = State.OK
            if value != "ok":
                state = State[params["%s_state" % duration]]
                infotext += "faulty"
            else:
                infotext += "successful"

            duration_val = persistence_data.get("%s_time_sec" % duration)
            if duration_val is not None and duration_val != -1:
                infotext += " (Duration: %s)" % render.timespan(duration_val)
            yield Result(state=state, summary=infotext)

    rdb_save_time = persistence_data.get("rdb_last_save_time")
    if rdb_save_time is not None:
        yield Result(
            state=State.OK, summary="Last successful RDB save: %s" % render.datetime(rdb_save_time)
        )

    rdb_changes = persistence_data.get("rdb_changes_since_last_save")
    if rdb_changes is not None:
        yield from check_levels_v1(
            int(rdb_changes),
            metric_name="changes_sld",
            levels_upper=params.get("rdb_changes_count"),
            render_func=lambda x: str(int(x)),
            label="Number of changes since last dump",
        )


check_plugin_redis_info_persistence = CheckPlugin(
    name="redis_info_persistence",
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
