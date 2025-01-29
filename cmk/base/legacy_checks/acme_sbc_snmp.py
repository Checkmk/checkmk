#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.acme.agent_based.lib import DETECT_ACME

check_info = {}

# comNET GmbH, Fabian Binder

# .1.3.6.1.4.1.9148.3.2.1.1.3 Health Score (apSysHealthScore)
# .1.3.6.1.4.1.9148.3.2.1.1.4 Health Status Description (apSysRedundancy)


def inventory_acme_sbc_snmp(info):
    yield None, {}


def check_acme_sbc_snmp(_no_item, params, info):
    map_states = {
        "0": (3, "unknown"),
        "1": (1, "initial"),
        "2": (0, "active"),
        "3": (0, "standby"),
        "4": (2, "out of service"),
        "5": (2, "unassigned"),
        "6": (1, "active (pending)"),
        "7": (1, "standby (pending)"),
        "8": (1, "out of service (pending)"),
        "9": (1, "recovery"),
    }

    try:
        score, state = info[0]
    except (IndexError, ValueError):
        return
    health_state, health_state_readable = map_states.get(state, (3, "unknown"))
    yield health_state, "Health state: %s" % (health_state_readable)

    try:
        score = int(score)
    except ValueError:
        yield 3, "Unknown score: %s" % score
        return
    warn, crit = params.get("levels_lower", (None, None))
    levels_msg = f" (warn/crit at or below {warn}%/{crit}%)"
    score_msg = "Score: %s%%" % score
    if crit is not None and score <= crit:
        yield 2, score_msg + levels_msg
    elif warn is not None and score <= warn:
        yield 1, score_msg + levels_msg
    else:
        yield 0, score_msg


def parse_acme_sbc_snmp(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["acme_sbc_snmp"] = LegacyCheckDefinition(
    name="acme_sbc_snmp",
    parse_function=parse_acme_sbc_snmp,
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.2.1.1",
        oids=["3", "4"],
    ),
    service_name="ACME SBC health",
    discovery_function=inventory_acme_sbc_snmp,
    check_function=check_acme_sbc_snmp,
    check_ruleset_name="acme_sbc_snmp",
    check_default_parameters={
        "levels_lower": (99, 75),
    },
)
