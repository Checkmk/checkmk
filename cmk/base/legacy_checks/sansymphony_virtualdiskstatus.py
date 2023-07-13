#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<sansymphony_virtualdiskstatus>>>
# testvmfs01 Online
# vmfs10 Online


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def parse_sansymphony_virtualdiskstatus(info):
    parsed = {}
    for line in info:
        parsed.setdefault(line[0], " ".join(line[1:]))
    return parsed


def check_sansymphony_virtualdiskstatus(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    state = 0 if data == "Online" else 2
    yield state, "Volume state is: %s" % data


def discover_sansymphony_virtualdiskstatus(section):
    yield from ((item, {}) for item in section)


check_info["sansymphony_virtualdiskstatus"] = LegacyCheckDefinition(
    parse_function=parse_sansymphony_virtualdiskstatus,
    service_name="sansymphony Virtual Disk %s",
    discovery_function=discover_sansymphony_virtualdiskstatus,
    check_function=check_sansymphony_virtualdiskstatus,
)
