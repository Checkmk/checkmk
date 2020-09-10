#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=wrong-import-order

from typing import (
    Iterable,
    Sequence,
)
from .agent_based_api.v1 import (
    all_of,
    any_of,
    contains,
    never_detect,
    register,
    SNMPTree,
    type_defs,
)
from .utils import if64, interfaces

SNMP_TREES = [
    SNMPTree(
        base=if64.BASE_OID,
        oids=if64.END_OIDS[:1] + [
            "31.1.1.1.1",  # 1 ifName (brocade and lancom have no useful information in ifDescr)
        ] + if64.END_OIDS[2:3] + [
            "31.1.1.1.15",  # 3 ifHighSpeed, 1000 means 1Gbit
        ] + if64.END_OIDS[4:-1] + [
            "2.2.1.2",  # -1 ifDescr, used in order to ignore some logical NICs
        ],
    ),
    SNMPTree(
        base=".1.3.6.1.4.1.2356.11.1.3.56.1",
        oids=[
            "1",
            "3",
        ],
    ),
]


def parse_if64_brocade_lancom(
    string_table: type_defs.SNMPStringByteTable,
    descriptions_to_ignore: Iterable[str],
) -> interfaces.Section:
    """
    >>> from pprint import pprint
    >>> pprint(parse_if64_brocade_lancom([
    ... [['1', 'eth0', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
    ...   '12', '13', 'eth0', [0, 12, 206, 149, 55, 128], 'description']],
    ... [['a', 'b']]],
    ... []))
    [Interface(index='1', descr='eth0', alias='eth0', type='2', speed=30000000, oper_status='1', in_octets=1, in_ucast=2, in_mcast=3, in_bcast=4, in_discards=5, in_errors=6, out_octets=7, out_ucast=8, out_mcast=9, out_bcast=10, out_discards=11, out_errors=12, out_qlen=13, phys_address=[0, 12, 206, 149, 55, 128], oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    >>> pprint(parse_if64_brocade_lancom([
    ... [['1', 'eth0', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
    ...   '12', '13', 'eth0', [0, 12, 206, 149, 55, 128], 'description']],
    ... [['a', 'b']]],
    ... ['descr']))
    []
    >>> pprint(parse_if64_brocade_lancom([
    ... [['1', 'eth0', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
    ...   '12', '13', 'eth0', [0, 12, 206, 149, 55, 128], 'Logical Network'],
    ...  ['2', 'eth1', '2', '30', '1', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
    ...   '12', '13', 'eth1', [0, 12, 206, 149, 55, 128], 'Logical Network']],
    ... [['eth0', 'migration-fun']]],
    ... ['descr']))
    [Interface(index='1', descr='eth0 Logical migration-fun', alias='eth0', type='2', speed=30000000, oper_status='1', in_octets=1, in_ucast=2, in_mcast=3, in_bcast=4, in_discards=5, in_errors=6, out_octets=7, out_ucast=8, out_mcast=9, out_bcast=10, out_discards=11, out_errors=12, out_qlen=13, phys_address=[0, 12, 206, 149, 55, 128], oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None),
     Interface(index='2', descr='eth1 Logical', alias='eth1', type='2', speed=30000000, oper_status='1', in_octets=1, in_ucast=2, in_mcast=3, in_bcast=4, in_discards=5, in_errors=6, out_octets=7, out_ucast=8, out_mcast=9, out_bcast=10, out_discards=11, out_errors=12, out_qlen=13, phys_address=[0, 12, 206, 149, 55, 128], oper_status_name='up', speed_as_text='', group=None, node=None, admin_status=None)]
    """

    if_table, ssid_table = string_table
    ssid_dict = {str(ssid_line[0]): str(ssid_line[1]) for ssid_line in ssid_table}
    new_info = []

    for line in if_table:
        description = str(line[-1])
        if any(
                description.startswith(descr_to_ignore)
                for descr_to_ignore in descriptions_to_ignore):
            continue

        name = str(line[1])
        if description.startswith("Logical Network"):
            ssid = ssid_dict.get(name)
            name += " Logical" + (" " + ssid if ssid else "")

        line[1] = name.strip()
        line[3] = if64.fix_if_64_highspeed(str(line[3]))
        new_info.append(line[:-1])

    return if64.generic_parse_if64([new_info])


# NOTE: THIS AN API VIOLATION, DO NOT REPLICATE THIS
# ==================================================================================================
from cmk.utils.type_defs import RuleSetName
from cmk.snmplib.type_defs import SNMPDetectSpec, SNMPRuleDependentDetectSpec
from cmk.base.api.agent_based.register import add_section_plugin, add_discovery_ruleset
from cmk.base.api.agent_based.register.section_plugins import create_snmp_section_plugin


def compute_detect_spec_if_brocade(if_disable_if64_hosts: Sequence[bool],) -> SNMPDetectSpec:
    r"""
    >>> compute_detect_spec_if_brocade([])
    [[('.1.3.6.1.2.1.1.1.0', '.*Brocade\\ VDX\\ Switch.*', True), ('.1.3.6.1.2.1.31.1.1.1.6.*', '.*', True)]]
    >>> compute_detect_spec_if_brocade([True])
    [[('.1.3.6.1.2.1.1.2.0', '(?!x)x', True)]]
    """
    if if64.is_disabled(if_disable_if64_hosts):
        return never_detect
    return all_of(contains(".1.3.6.1.2.1.1.1.0", "Brocade VDX Switch"), if64.HAS_ifHCInOctets)


section_plugin = create_snmp_section_plugin(
    name="if_brocade",
    parse_function=lambda string_table: parse_if64_brocade_lancom(
        string_table,
        ["Point-2-Point"],
    ),
    trees=SNMP_TREES,
    detect_spec=never_detect,  # does not matter what we put here
    rule_dependent_detect_spec=SNMPRuleDependentDetectSpec(
        [RuleSetName('if_disable_if64_hosts')],
        compute_detect_spec_if_brocade,
    ),
    supersedes=['if', 'if64', 'if64adm'],
)
add_section_plugin(section_plugin)
assert section_plugin.rule_dependent_detect_spec
for discovery_ruleset in section_plugin.rule_dependent_detect_spec.rulesets:
    add_discovery_ruleset(discovery_ruleset)


def compute_detect_spec_if_lancom(if_disable_if64_hosts: Sequence[bool],) -> SNMPDetectSpec:
    r"""
    >>> compute_detect_spec_if_lancom([])
    [[('.1.3.6.1.2.1.1.1.0', '.*LANCOM.*', True)], [('.1.3.6.1.2.1.1.1.0', '.*ELSA.*', True)], [('.1.3.6.1.2.1.1.1.0', '.*T\\-Systems.*', True)], [('.1.3.6.1.2.1.1.1.0', '.*LAN\\ R800V.*', True), ('.1.3.6.1.2.1.31.1.1.1.6.*', '.*', True)]]
    >>> compute_detect_spec_if_lancom([True])
    [[('.1.3.6.1.2.1.1.2.0', '(?!x)x', True)]]
    """
    sys_description_oid = ".1.3.6.1.2.1.1.1.0"
    if if64.is_disabled(if_disable_if64_hosts):
        return never_detect
    return any_of(
        any_of(*(contains(sys_description_oid, name) for name in ("LANCOM", "ELSA", "T-Systems")),),
        all_of(
            contains(sys_description_oid, "LAN R800V"),
            if64.HAS_ifHCInOctets,
        ),
    )


section_plugin = create_snmp_section_plugin(
    name="if_lancom",
    parse_function=lambda string_table: parse_if64_brocade_lancom(
        string_table,
        ["P2P", "Point-2-Point"],
    ),
    trees=SNMP_TREES,
    detect_spec=never_detect,  # does not matter what we put here
    rule_dependent_detect_spec=SNMPRuleDependentDetectSpec(
        [RuleSetName('if_disable_if64_hosts')],
        compute_detect_spec_if_lancom,
    ),
    supersedes=['if', 'if64', 'if64adm'],
)
add_section_plugin(section_plugin)
assert section_plugin.rule_dependent_detect_spec
for discovery_ruleset in section_plugin.rule_dependent_detect_spec.rulesets:
    add_discovery_ruleset(discovery_ruleset)
# ==================================================================================================

register.check_plugin(
    name="if_brocade",
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

register.check_plugin(
    name="if_lancom",
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
