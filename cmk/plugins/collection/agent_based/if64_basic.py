#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import CheckPlugin, CheckResult, RuleSetType
from cmk.plugins.lib import interfaces


def check_interfaces(
    item: str,
    params: Mapping[str, Any],
    section: interfaces.Section[interfaces.TInterfaceType],
) -> CheckResult:
    yield from interfaces.check_multiple_interfaces(
        item=item,
        params=params,
        section=section,
        group_name="Interface group",
    )


check_plugin_interfaces = CheckPlugin(
    name="interfaces",
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=interfaces.discover_interfaces,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_interfaces,
    cluster_check_function=interfaces.cluster_check,
)
