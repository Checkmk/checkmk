#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


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
from cmk.plugins.stormshield.lib import DETECT_STORMSHIELD


def discover_stormshield_info(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_stormshield_info(section: StringTable) -> CheckResult:
    for model, version, serial, sysname, syslanguage in section:
        yield Result(
            state=State.OK,
            summary=f"Model: {model}, Version: {version}, Serial: {serial}, SysName: {sysname}, \
            SysLanguage: {syslanguage}",
        )


def parse_stormshield_info(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_stormshield_info = SimpleSNMPSection(
    name="stormshield_info",
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.0",
        oids=["1", "2", "3", "4", "5"],
    ),
    parse_function=parse_stormshield_info,
)


check_plugin_stormshield_info = CheckPlugin(
    name="stormshield_info",
    service_name="Stormshield Info",
    discovery_function=discover_stormshield_info,
    check_function=check_stormshield_info,
)
