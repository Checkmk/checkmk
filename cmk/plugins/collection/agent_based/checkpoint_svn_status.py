#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.checkpoint import DETECT


def inventory_checkpoint_svn_status(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_checkpoint_svn_status(section: StringTable) -> CheckResult:
    if section:
        major, minor, code, description = section[0]
        ver = f"v{major}.{minor}"
        if int(code) != 0:
            yield Result(state=State.CRIT, summary=description)
            return
        yield Result(state=State.OK, summary="OK (%s)" % ver)


def parse_checkpoint_svn_status(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_checkpoint_svn_status = SimpleSNMPSection(
    name="checkpoint_svn_status",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6",
        oids=["2", "3", "101", "103"],
    ),
    parse_function=parse_checkpoint_svn_status,
)
check_plugin_checkpoint_svn_status = CheckPlugin(
    name="checkpoint_svn_status",
    service_name="SVN Status",
    discovery_function=inventory_checkpoint_svn_status,
    check_function=check_checkpoint_svn_status,
)
