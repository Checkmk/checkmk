#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<splunk_health>>>
# Overall_state red
# File_monitor_input red
# File_monitor_input Tailreader-0 red
# File_monitor_input Batchreader-0 green
# Data_forwarding red
# Data_forwarding Splunk-2-splunk_forwarding red
# Index_processor green
# Index_processor Index_optimization green
# Index_processor Buckets green
# Index_processor Disk_space green


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def parse_splunk_health(string_table):
    parsed = {}

    for state_detail in string_table:
        try:
            if len(state_detail) == 2:
                name, health = state_detail
                parsed[name.replace("_", " ")] = {"health": health, "feature": {}}
            else:
                name, feature, feature_health = state_detail
                parsed[name.replace("_", " ")]["feature"].update({feature: feature_health})

        except (IndexError, ValueError):
            pass

    return parsed


def inventory_splunk_health(parsed):
    yield None, {}


def check_splunk_health(_no_item, params, parsed):
    long_output = ""

    for key in [
        ("Overall state"),
        ("File monitor input"),
        ("Index processor"),
        ("Data forwarding"),
    ]:
        try:
            # some functions may be missing, eg. Data forwarding in OK states
            health = parsed[key]["health"]
        except KeyError:
            continue

        yield params[health], f"{key}: {health}"

        for name in sorted(parsed[key]["feature"]):
            if name != "Overall state":
                long_output += "{} - State: {}\n".format(
                    name.replace("_", " "),
                    parsed[key]["feature"][name],
                )

    yield 0, "\n%s" % long_output


check_info["splunk_health"] = LegacyCheckDefinition(
    parse_function=parse_splunk_health,
    service_name="Splunk Health",
    discovery_function=inventory_splunk_health,
    check_function=check_splunk_health,
    check_ruleset_name="splunk_health",
    check_default_parameters={
        "green": 0,
        "yellow": 1,
        "red": 2,
    },
)
