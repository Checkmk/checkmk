#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.elphase import check_elphase

check_info = {}


def discover_apc_rackpdu_power(section):
    yield from ((item, {}) for item in section)


check_info["apc_rackpdu_power"] = LegacyCheckDefinition(
    name="apc_rackpdu_power",
    service_name="PDU %s",
    discovery_function=discover_apc_rackpdu_power,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
)
