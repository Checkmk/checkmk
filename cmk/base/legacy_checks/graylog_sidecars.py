#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.base.check_legacy_includes.graylog import handle_iso_utc_to_localtimestamp, json

check_info = {}

# <<<graylog_sidecars>>>
# {"sort": "node_name", "pagination": {"count": 1, "per_page": 50, "total": 1,
# "page": 1}, "sidecars": [{"co  llectors": null, "node_name": "testserver",
# "assignments": [], "node_id": "31c3e8f9-a6b2-41d4-be78-f6273c3cb0e5", "n
# ode_details": {"metrics": {"disks_75": ["/snap/gnome-calculator/501
# (100%)", "/snap/core/7713 (100%)", "/snap/gnome-  calculator/406 (100%)",
# "/snap/gtk-common-themes/1313 (100%)", "/snap/core18/1192 (100%)",
# "/snap/spotify/35 (100%)"  , "/snap/gnome-characters/317 (100%)",
# "/snap/gnome-3-26-1604/90 (100%)", "/snap/gnome-3-28-1804/71 (100%)",
# "/snap/  gnome-3-26-1604/92 (100%)", "/snap/gtk-common-themes/1198 (100%)",
# "/snap/gnome-logs/73 (100%)", "/snap/gnome-logs/8  1 (100%)",
# "/snap/gnome-characters/296 (100%)", "/snap/gnome-3-28-1804/67 (100%)",
# "/snap/core18/1144 (100%)", "/sna  p/gnome-system-monitor/100 (100%)",
# "/snap/gnome-system-monitor/95 (100%)", "/snap/core/7396 (100%)",
# "/snap/spotify  /36 (100%)"], "load_1": 0.49, "cpu_idle": 95.0}, "ip":
# "10.3.2.62", "operating_system": "Linux", "status": {"status"  : 1,
# "message": "Received no ping signal from sidecar", "collectors": []},
# "log_file_list": null}, "active": false,   "sidecar_version": "1.0.2",
# "last_seen": "2019-10-10T09:56:29.303Z"}], "filters": null, "only_active":
# false, "query  ": "", "total": 1, "order": "asc"}


def parse_graylog_sidecars(string_table):
    parsed = {}

    for line in string_table:
        sidecar_data = json.loads(line[0])

        sidecar_nodename = sidecar_data.get("node_name")
        if sidecar_nodename is None:
            continue

        parsed.setdefault(
            sidecar_nodename,
            {
                "active": sidecar_data.get("active"),
                "collectors": sidecar_data.get("node_details", {})
                .get("status", {})
                .get("collectors"),
                "collector_msg": sidecar_data.get("node_details", {})
                .get("status", {})
                .get("message"),
                "last_seen": sidecar_data.get("last_seen"),
                "status": sidecar_data.get("node_details", {}).get("status", {}).get("status"),
            },
        )

    return parsed


def check_graylog_sidecars(item, params, parsed):
    if not (item_data := parsed.get(item)):
        return

    active_msg = item_data.get("active")
    if active_msg is not None:
        active_state = 0
        msg = str(active_msg).replace("True", "yes").replace("False", "no")
        if not active_msg:
            active_state = params.get("active_state", 2)

        yield active_state, "Active: %s" % msg

    last_seen = item_data.get("last_seen")
    if last_seen is not None:
        local_timestamp = handle_iso_utc_to_localtimestamp(last_seen)
        age = time.time() - local_timestamp

        yield 0, "Last seen: %s" % render.datetime(local_timestamp)

        yield check_levels(
            age,
            None,
            params.get("last_seen"),
            human_readable_func=render.timespan,
            infoname="Before",
        )

    collector_state = _handle_collector_states(item_data.get("status", 3), params)
    collector_msg = item_data.get("collector_msg")
    if collector_msg is not None:
        msg = collector_msg.split("/")
        if len(msg) == 3:
            for num_collector in msg:
                count, status = num_collector.strip().split(" ")

                collector_nr_levels = params.get("%s_upper" % status, (None, None))
                collector_nr_levels_lower = params.get("%s_lower" % status, (None, None))

                yield check_levels(
                    int(count),
                    "collectors_%s" % status,
                    collector_nr_levels + collector_nr_levels_lower,
                    human_readable_func=int,
                    infoname="Collectors %s" % status,
                )

        else:
            yield collector_state, "Collectors: %s" % collector_msg

    collector_data = item_data.get("collectors")
    if collector_data is not None:
        long_output = []
        for collector in collector_data:
            long_output_str = ""

            collector_id = collector.get("collector_id")
            if collector_id is not None:
                long_output_str += "ID: %s" % collector_id

            collector_msg = collector.get("message")
            if collector_msg is not None:
                long_output_str += ", Message: %s" % collector_msg

            collector_state = _handle_collector_states(collector.get("status", 3), params)

            long_output.append((collector_state, long_output_str))

    if long_output:
        max_state = max(state for state, _infotext in long_output)

        yield max_state, "see long output for more details"

        for state, line in long_output:
            yield state, "\n%s" % line


def _handle_collector_states(collector_state, params):
    if collector_state == 0:
        return params.get("running", 0)
    # "Received no ping signal from sidecar"
    if collector_state == 1:
        return params.get("no_ping", 2)
    if collector_state == 2:
        return params.get("failing", 2)
    if collector_state == 3:
        return params.get("stopped", 2)

    return 3


def discover_graylog_sidecars(section):
    yield from ((item, {}) for item in section)


check_info["graylog_sidecars"] = LegacyCheckDefinition(
    name="graylog_sidecars",
    parse_function=parse_graylog_sidecars,
    service_name="Graylog Sidecar %s",
    discovery_function=discover_graylog_sidecars,
    check_function=check_graylog_sidecars,
    check_ruleset_name="graylog_sidecars",
    check_default_parameters={
        "running_lower": (1, 0),
        "stopped_upper": (1, 1),
        "failing_upper": (1, 1),
    },
)
