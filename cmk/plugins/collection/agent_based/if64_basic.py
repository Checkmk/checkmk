#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, RuleSetType
from cmk.plugins.lib import if64, interfaces


def discover_interfaces(
    params: Sequence[Mapping[str, Any]],
    section_interfaces: interfaces.Section[interfaces.TInterfaceType] | None,
    section_if_names: if64.IfNamesSection | None,
) -> DiscoveryResult:
    if section_interfaces is None:
        return
    if64.add_names_to_ifaces(section_interfaces, section_if_names)
    yield from interfaces.discover_interfaces(params, section_interfaces)


def check_interfaces(
    item: str,
    params: Mapping[str, Any],
    section_interfaces: interfaces.Section[interfaces.TInterfaceType] | None,
    section_if_names: if64.IfNamesSection | None,
) -> CheckResult:
    if section_interfaces is None:
        return
    if64.add_names_to_ifaces(section_interfaces, section_if_names)
    yield from interfaces.check_multiple_interfaces(
        item=item,
        params=params,
        section=section_interfaces,
        group_name="Interface group",
    )


def cluster_check_interfaces(
    item: str,
    params: Mapping[str, Any],
    section_interfaces: Mapping[str, interfaces.Section[interfaces.TInterfaceType] | None],
    section_if_names: Mapping[str, if64.IfNamesSection | None],
) -> CheckResult:
    for node_name, node_section in section_interfaces.items():
        if node_section is not None:
            if64.add_names_to_ifaces(node_section, section_if_names.get(node_name))
    yield from interfaces.cluster_check(item, params, section_interfaces)


check_plugin_interfaces = CheckPlugin(
    name="interfaces",
    sections=["interfaces", "if_names"],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_interfaces,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_interfaces,
    cluster_check_function=cluster_check_interfaces,
)
