#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.huawei.lib import DETECT_HUAWEI_OSN

check_info = {}

# The dBm should not get too low. So we check only for lower levels


def discover_huawei_osn_laser(info):
    for line in info:
        yield (line[0], None)


def check_huawei_osn_laser(item, params, info):
    def check_state(reading, params):
        warn, crit = params
        if reading <= crit:
            state = 2
        elif reading <= warn:
            state = 1
        else:
            state = 0

        if state:
            return state, f"(warn/crit below {warn}/{crit} dBm)"
        return 0, ""

    for line in info:
        if item == line[0]:
            dbm_in = float(line[2]) / 10
            dbm_out = float(line[1]) / 10

            warn_in, crit_in = params["levels_low_in"]
            warn_out, crit_out = params["levels_low_out"]

            # In
            yield (
                0,
                "In: %.1f dBm" % dbm_in,
                [
                    ("input_signal_power_dBm", dbm_in, warn_in, crit_in),
                ],
            )
            yield check_state(dbm_in, (warn_in, crit_in))

            # And out
            yield (
                0,
                "Out: %.1f dBm" % dbm_out,
                [("output_signal_power_dBm", dbm_out, warn_out, crit_out)],
            )
            yield check_state(dbm_out, (warn_out, crit_out))

            # FEC Correction
            fec_before = line[3]
            fec_after = line[4]
            if not fec_before == "" and not fec_after == "":
                yield 0, f"FEC Correction before/after: {fec_before}/{fec_after}"


def parse_huawei_osn_laser(string_table: StringTable) -> StringTable:
    return string_table


check_info["huawei_osn_laser"] = LegacyCheckDefinition(
    name="huawei_osn_laser",
    parse_function=parse_huawei_osn_laser,
    detect=DETECT_HUAWEI_OSN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.2.25.3.40.50.119.10.1",
        oids=["6.200", "2.200", "2.203", "2.252", "2.253"],
    ),
    service_name="Laser %s",
    discovery_function=discover_huawei_osn_laser,
    check_function=check_huawei_osn_laser,
    check_ruleset_name="huawei_osn_laser",
    check_default_parameters={
        "levels_low_in": (-160, -180),
        "levels_low_out": (-35, -40),
    },
)
