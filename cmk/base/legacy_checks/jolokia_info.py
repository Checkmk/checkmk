#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_jolokia_info(string_table):
    parsed = {}
    for line in string_table:
        parsed.setdefault(line[0], []).append(line[1:])
    return parsed


def check_jolokia_info(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    line = data[0]
    # Inform user of non-working agent plugin, eg. missing json library
    if item == "Error:":
        yield 3, " ".join(line)
        return

    if line[0] == "ERROR" or len(line) < 3:
        yield 2, " ".join(line) or "Unknown error in plug-in"
        return

    product = line[0]
    jolokia_version = line[-1]
    version = " ".join(line[1:-1])
    yield 0, f"{product.title()} {version} (Jolokia version {jolokia_version})"


def discover_jolokia_info(section):
    yield from ((item, {}) for item in section)


check_info["jolokia_info"] = LegacyCheckDefinition(
    name="jolokia_info",
    parse_function=parse_jolokia_info,
    service_name="JVM %s",
    discovery_function=discover_jolokia_info,
    check_function=check_jolokia_info,
)
