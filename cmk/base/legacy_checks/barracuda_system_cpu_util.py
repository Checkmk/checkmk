#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.plugins.barracuda.lib import DETECT_BARRACUDA

check_info = {}

# .1.3.6.1.4.1.20632.2.13 3

# Suggested by customer


def discover_barracuda_system_cpu_util(info):
    yield None, {}


def check_barracuda_system_cpu_util(_no_item, params, info):
    return check_cpu_util(int(info[0][0]), params)


def parse_barracuda_system_cpu_util(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["barracuda_system_cpu_util"] = LegacyCheckDefinition(
    name="barracuda_system_cpu_util",
    parse_function=parse_barracuda_system_cpu_util,
    detect=DETECT_BARRACUDA,
    # The barracuda spam firewall does not response or returns a timeout error
    # executing 'snmpwalk' on whole tables. But we can workaround here specifying
    # all needed OIDs. Then we can use 'snmpget' and 'snmpwalk' on these single OIDs.,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20632.2",
        oids=["13"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_barracuda_system_cpu_util,
    check_function=check_barracuda_system_cpu_util,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
