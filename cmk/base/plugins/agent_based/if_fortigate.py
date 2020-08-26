#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v0 import (
    register,
    SNMPTree,
    startswith,
)
from .utils import if64, interfaces

register.snmp_section(
    name="if_fortigate",
    parse_function=if64.parse_if64_if6adm,
    trees=[
        SNMPTree(
            base=if64.BASE_OID,
            oids=if64.END_OIDS,
        ),
    ],
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356"),
    supersedes=['if', 'if64', 'if64adm'],
)

register.check_plugin(
    name="if_fortigate",
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type="all",
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=if64.check_if64,
    cluster_check_function=interfaces.cluster_check,
)
