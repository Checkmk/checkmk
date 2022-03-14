#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Mapping, Optional, Sequence

from .agent_based_api.v1 import register, SNMPTree, type_defs
from .utils import if64, interfaces

If64AdmSection = Sequence[str]


def parse_if64adm(string_table: type_defs.StringTable) -> If64AdmSection:
    return [sub_table[0] for sub_table in string_table]


register.snmp_section(
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
register.snmp_section(
    name="if64adm",
    parse_function=parse_if64adm,
    fetch=SNMPTree(
        base=if64.BASE_OID,
        oids=["2.2.1.7"],  # ifAdminStatus
    ),
    detect=if64.HAS_ifHCInOctets,
)


def _add_admin_status_to_ifaces(
    section_if64: interfaces.Section,
    section_if64adm: Optional[If64AdmSection],
) -> None:
    if section_if64adm is None or len(section_if64) != len(section_if64adm):
        return
    for iface, admin_status in zip(section_if64, section_if64adm):
        iface.admin_status = admin_status


def discover_if64(
    params: Sequence[Mapping[str, Any]],
    section_if64: Optional[interfaces.Section],
    section_if64adm: Optional[If64AdmSection],
) -> type_defs.DiscoveryResult:
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
    section_if64: Optional[interfaces.Section],
    section_if64adm: Optional[If64AdmSection],
) -> type_defs.CheckResult:
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
    section_if64: Mapping[str, Optional[interfaces.Section]],
    section_if64adm: Mapping[str, Optional[If64AdmSection]],
) -> type_defs.CheckResult:

    sections_w_admin_status: Dict[str, interfaces.Section] = {}
    for node_name, node_section_if64 in section_if64.items():
        if node_section_if64 is not None:
            _add_admin_status_to_ifaces(node_section_if64, section_if64adm[node_name])
            sections_w_admin_status[node_name] = node_section_if64

    yield from interfaces.cluster_check(
        item,
        params,
        sections_w_admin_status,
    )


register.check_plugin(
    name="if64",
    sections=["if64", "if64adm"],
    service_name="Interface %s",
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_if64,
    check_ruleset_name="if",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_if64,
    cluster_check_function=cluster_check_if64,
)
