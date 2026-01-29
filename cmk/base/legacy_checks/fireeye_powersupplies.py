#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fireeye import check_fireeye_states
from cmk.plugins.fireeye.lib import DETECT

check_info = {}

# .1.3.6.1.4.1.25597.11.3.1.1.0 Good --> FE-FIREEYE-MIB::fePowerSupplyOverallStatus.0
# .1.3.6.1.4.1.25597.11.3.1.2.0 1 --> FE-FIREEYE-MIB::fePowerSupplyOverallIsHealthy.0


def check_fireeye_powersupplies(_no_item, _no_params, info):
    status, health = info[0]
    for text, (state, state_readable) in check_fireeye_states(
        [(status, "Status"), (health, "Health")]
    ).items():
        yield state, f"{text}: {state_readable}"


def parse_fireeye_powersupplies(string_table: StringTable) -> StringTable:
    return string_table


def discover_fireeye_powersupplies(info):
    yield from [(None, None)] if info else []


check_info["fireeye_powersupplies"] = LegacyCheckDefinition(
    name="fireeye_powersupplies",
    parse_function=parse_fireeye_powersupplies,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.3.1",
        oids=["1", "2"],
    ),
    service_name="Power supplies summary",
    discovery_function=discover_fireeye_powersupplies,
    check_function=check_fireeye_powersupplies,
)
