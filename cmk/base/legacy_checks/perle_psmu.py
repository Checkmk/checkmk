#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.config import check_info


def inventory_perle_psmu(parsed, what_state):
    for unit, values in parsed.items():
        if values[what_state][1] != "not present":
            yield unit, {}


def check_perle_psmu_powersupplies(item, params, parsed):
    if item in parsed:
        state, state_readable = parsed[item]["psustate"]
        yield state, "Status: %s" % state_readable
        for res in check_elphase(item, params, parsed):
            yield res


check_info["perle_psmu"] = LegacyCheckDefinition(
    # section is already migrated!
    discovery_function=lambda info: inventory_perle_psmu(info, "psustate"),
    check_function=check_perle_psmu_powersupplies,
    service_name="Power supply %s",
    check_ruleset_name="el_inphase",
)


def check_perle_psmu_fans(item, _no_params, parsed):
    if item in parsed:
        state, state_readable = parsed[item]["fanstate"]
        return state, "Status: %s" % state_readable
    return None


check_info["perle_psmu.fan"] = LegacyCheckDefinition(
    discovery_function=lambda info: inventory_perle_psmu(info, "fanstate"),
    check_function=check_perle_psmu_fans,
    service_name="Fan %s",
)
