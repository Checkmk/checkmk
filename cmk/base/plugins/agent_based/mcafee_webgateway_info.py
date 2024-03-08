#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    register,
    Result,
    Service,
    SNMPTree,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

from cmk.plugins.lib import mcafee_gateway


def parse_mcafee_webgateway_info(string_table: StringTable) -> StringTable:
    return string_table


register.snmp_section(
    name="mcafee_webgateway_info",
    detect=mcafee_gateway.DETECT_WEB_GATEWAY,
    parse_function=parse_mcafee_webgateway_info,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.7.1",
        oids=["3", "9"],
    ),
)


def discovery_mcafee_webgateway_info(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_mcafee_webgateway_info(section: StringTable) -> CheckResult:
    version, revision = section[0]
    yield Result(state=State.OK, summary=f"Product version: {version}, Revision: {revision}")


register.check_plugin(
    name="mcafee_webgateway_info",
    discovery_function=discovery_mcafee_webgateway_info,
    check_function=check_mcafee_webgateway_info,
    service_name="Web gateway info",
)
