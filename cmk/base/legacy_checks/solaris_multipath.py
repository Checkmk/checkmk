#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Example output:
# <<<solaris_multipath>>>
# /dev/rdsk/c4t600601608CB02A00DCFD2EEB19A0E111d0s2 4 4

# Note: the number of total paths is not correct. After maintainance
# they is too high. Also in case of broken paths the number of total
# paths sometimes changes. So we just use that for informational
# output. The discovery remembers the number of operational paths
# and we check agains that later.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_solaris_multipath(info):
    for device, _total, operational in info:
        item = device.split("/")[-1]
        yield item, {"levels": int(operational)}


def check_solaris_multipath(item, params, info):
    for device, total, operational in info:
        if item == device.split("/")[-1]:
            operational = int(operational)
            total = int(total)

            # TODO: Clean this up! Compare to the multipath plugin.

            infotext = "%d paths operational, %d paths total" % (operational, total)

            levels = params.get("levels")
            if levels is None:
                state = 1
                infotext += ", expected paths unknown, please redo service discovery"
            elif isinstance(levels, tuple):
                warn, crit = levels
                warn_num = (warn / 100.0) * total
                crit_num = (crit / 100.0) * total
                levels = " (Warning/ Critical at %d/ %d)" % (warn_num, crit_num)
                info = "paths active: %d" % (operational)
                if operational <= crit_num:
                    return 2, info + levels
                if operational <= warn_num:
                    return 1, info + levels
                return 0, info

            expected = int(levels)  # should be int, just for legacy reasons
            if operational > expected:
                state = 1
            elif expected == operational:
                state = 0
            elif expected >= operational * 2:  # less than half of paths operational
                state = 2
            else:
                state = 1
            if state:
                infotext += ", %d paths expected to be operational" % expected

            return state, infotext
    return None


def parse_solaris_multipath(string_table: StringTable) -> StringTable:
    return string_table


check_info["solaris_multipath"] = LegacyCheckDefinition(
    name="solaris_multipath",
    parse_function=parse_solaris_multipath,
    service_name="Multipath %s",
    discovery_function=discover_solaris_multipath,
    check_function=check_solaris_multipath,
    check_ruleset_name="multipath",
    check_default_parameters={},  # overwritten by discovery
)
