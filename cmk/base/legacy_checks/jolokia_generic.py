#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import check_levels, discover, get_rate, LegacyCheckDefinition
from cmk.base.check_legacy_includes.jolokia import jolokia_basic_split
from cmk.base.config import check_info


def parse_jolokia_generic(info):
    value: str | float
    parsed = {}
    for line in info:
        try:
            instance, mbean, value, type_ = jolokia_basic_split(line, 4)
            if type_ in ("rate", "number"):
                value = float(value)
        except ValueError:
            continue
        item = "%s MBean %s" % (instance, mbean)
        parsed[item] = {"value": value, "type": type_}

    return parsed


# .
#   .--String--------------------------------------------------------------.
#   |                    ____  _        _                                  |
#   |                   / ___|| |_ _ __(_)_ __   __ _                      |
#   |                   \___ \| __| '__| | '_ \ / _` |                     |
#   |                    ___) | |_| |  | | | | | (_| |                     |
#   |                   |____/ \__|_|  |_|_| |_|\__, |                     |
#   |                                           |___/                      |
#   '----------------------------------------------------------------------'


def check_jolokia_generic_string(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    value = data["value"]

    search_strings = params.get("match_strings", [])
    for search_string, status in search_strings:
        if search_string in value:
            yield status, "%s: %s matches" % (value, search_string)
            return

    yield params.get("default_status", 0), value


check_info["jolokia_generic.string"] = LegacyCheckDefinition(
    discovery_function=discover(lambda key, data: data.get("type") == "string"),
    check_function=check_jolokia_generic_string,
    service_name="JVM %s",
    check_ruleset_name="generic_string",
)

# .
#   .--Rate----------------------------------------------------------------.
#   |                         ____       _                                 |
#   |                        |  _ \ __ _| |_ ___                           |
#   |                        | |_) / _` | __/ _ \                          |
#   |                        |  _ < (_| | ||  __/                          |
#   |                        |_| \_\__,_|\__\___|                          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_jolokia_generic_rate(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    rate = get_rate(item, time.time(), data["value"])
    levels = params.get("levels", (None, None)) + params.get("levels_lower", (None, None))
    yield check_levels(rate, "generic_rate", levels)


check_info["jolokia_generic.rate"] = LegacyCheckDefinition(
    discovery_function=discover(lambda key, data: data.get("type") == "rate"),
    check_function=check_jolokia_generic_rate,
    service_name="JVM %s",
    check_ruleset_name="generic_rate",
)

# .
#   .--Number--------------------------------------------------------------.
#   |                _   _                 _                               |
#   |               | \ | |_   _ _ __ ___ | |__   ___ _ __                 |
#   |               |  \| | | | | '_ ` _ \| '_ \ / _ \ '__|                |
#   |               | |\  | |_| | | | | | | |_) |  __/ |                   |
#   |               |_| \_|\__,_|_| |_| |_|_.__/ \___|_|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_jolokia_generic(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    levels = params.get("levels", (None, None)) + params.get("levels_lower", (None, None))
    yield check_levels(data["value"], "generic_number", levels)
    return


check_info["jolokia_generic"] = LegacyCheckDefinition(
    discovery_function=discover(lambda key, data: data.get("type") == "number"),
    check_function=check_jolokia_generic,
    parse_function=parse_jolokia_generic,
    service_name="JVM %s",
    check_ruleset_name="generic_number",
)
