#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    RuleSetType,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib import if64, interfaces

If64AdmSection = Sequence[str]


def parse_if64adm(string_table: StringTable) -> If64AdmSection:
    return [sub_table[0] for sub_table in string_table]


snmp_section_if64 = SimpleSNMPSection(
    name="if64",
    parse_function=if64.parse_if64,
    fetch=SNMPTree(
        base=if64.BASE_OID,
        oids=if64.END_OIDS,
    ),
    detect=if64.HAS_ifHCInOctets,
    supersedes=["if", "statgrab_net"],
)

# Note: This section is by default deactivated (hard-coded in
# cmk.base.config.disabled_snmp_sections) to reduce SNMP traffic. To activate it, use the SNMP
# Rulespec snmp_exclude_sections.
snmp_section_if64adm = SimpleSNMPSection(
    name="if64adm",
    parse_function=parse_if64adm,
    fetch=SNMPTree(
        base=if64.BASE_OID,
        oids=["2.2.1.7"],  # ifAdminStatus
    ),
    detect=if64.HAS_ifHCInOctets,
)


def _add_admin_status_to_ifaces(
    section_if64: interfaces.Section[interfaces.TInterfaceType],
    section_if64adm: If64AdmSection | None,
) -> None:
    if section_if64adm is None or len(section_if64) != len(section_if64adm):
        return
    for iface, admin_status in zip(section_if64, section_if64adm):
        iface.attributes.admin_status = admin_status


def discover_if64(
    params: Sequence[Mapping[str, Any]],
    section_if64: interfaces.Section[interfaces.TInterfaceType] | None,
    section_if64adm: If64AdmSection | None,
) -> DiscoveryResult:
    if section_if64 is None:
        return
    _add_admin_status_to_ifaces(section_if64, section_if64adm)
    yield from interfaces.discover_interfaces(
        params,
        section_if64,
    )


def check_if64(
    item: str,
    params: Mapping[str, Any],
    section_if64: interfaces.Section[interfaces.TInterfaceType] | None,
    section_if64adm: If64AdmSection | None,
) -> CheckResult:
    if section_if64 is None:
        return
    _add_admin_status_to_ifaces(section_if64, section_if64adm)
    yield from if64.generic_check_if64(
        item,
        params,
        section_if64,
    )


def cluster_check_if64(
    item: str,
    params: Mapping[str, Any],
    section_if64: Mapping[str, interfaces.Section[interfaces.TInterfaceType] | None],
    section_if64adm: Mapping[str, If64AdmSection | None],
) -> CheckResult:
    sections_w_admin_status: dict[str, interfaces.Section[interfaces.TInterfaceType]] = {}
    for node_name, node_section_if64 in section_if64.items():
        if node_section_if64 is not None:
            _add_admin_status_to_ifaces(node_section_if64, section_if64adm[node_name])
            sections_w_admin_status[node_name] = node_section_if64

    yield from interfaces.cluster_check(
        item,
        params,
        sections_w_admin_status,
    )


check_plugin_if64 = CheckPlugin(
    name="if64",
    sections=["if64", "if64adm"],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_if64,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_if64,
    cluster_check_function=cluster_check_if64,
)
