#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.plugins.enterasys.lib import DETECT_ENTERASYS

check_info = {}


def discover_enterasys_cpu_util(info):
    # [:-2] to remove the oid end
    return [(x[0][:-2], {}) for x in info]


def check_enterasys_cpu_util(item, params, info):
    for core, util in info:
        if item == core[:-2]:
            usage = int(util) / 10.0
            return check_cpu_util(usage, params)
    return None


def parse_enterasys_cpu_util(string_table: StringTable) -> StringTable:
    return string_table


check_info["enterasys_cpu_util"] = LegacyCheckDefinition(
    name="enterasys_cpu_util",
    parse_function=parse_enterasys_cpu_util,
    detect=DETECT_ENTERASYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5624.1.2.49.1.1.1.1",
        oids=[OIDEnd(), "3"],
    ),
    service_name="CPU util %s",
    discovery_function=discover_enterasys_cpu_util,
    check_function=check_enterasys_cpu_util,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={
        "levels": (90.0, 95.0),
    },
)
