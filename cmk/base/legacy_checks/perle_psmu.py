#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.elphase import check_elphase

check_info = {}


def inventory_perle_psmu(parsed, what_state):
    for unit, values in parsed.items():
        if values[what_state][1] != "not present":
            yield unit, {}


def check_perle_psmu_powersupplies(item, params, parsed):
    if item in parsed:
        state, state_readable = parsed[item]["psustate"]
        yield state, "Status: %s" % state_readable
        yield from check_elphase(item, params, parsed)


def discover_perle_psmu(info):
    return inventory_perle_psmu(info, "psustate")


check_info["perle_psmu"] = LegacyCheckDefinition(
    name="perle_psmu",
    # section is already migrated!
    service_name="Power supply %s",
    discovery_function=discover_perle_psmu,
    check_function=check_perle_psmu_powersupplies,
    check_ruleset_name="el_inphase",
)


def check_perle_psmu_fans(item, _no_params, parsed):
    if item in parsed:
        state, state_readable = parsed[item]["fanstate"]
        return state, "Status: %s" % state_readable
    return None


def discover_perle_psmu_fan(info):
    return inventory_perle_psmu(info, "fanstate")


check_info["perle_psmu.fan"] = LegacyCheckDefinition(
    name="perle_psmu_fan",
    service_name="Fan %s",
    sections=["perle_psmu"],
    discovery_function=discover_perle_psmu_fan,
    check_function=check_perle_psmu_fans,
)
