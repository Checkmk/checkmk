#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=wrong-import-order

from .agent_based_api.v1 import (
    never_detect,
    register,
    SNMPTree,
)
from .utils import if64, interfaces

# NOTE: THIS AN API VIOLATION, DO NOT REPLICATE THIS
# ==================================================================================================
from cmk.utils.type_defs import RuleSetName
from cmk.snmplib.type_defs import SNMPDetectSpec, SNMPRuleDependentDetectSpec
from cmk.base.api.agent_based.register import add_section_plugin, add_discovery_ruleset
from cmk.base.api.agent_based.register.section_plugins import create_snmp_section_plugin


def compute_detect_spec_if64(use_if64adm: if64.BinaryHostRules,) -> SNMPDetectSpec:
    """
    >>> compute_detect_spec_if64([])
    [[('.1.3.6.1.2.1.31.1.1.1.6.*', '.*', True)]]
    >>> compute_detect_spec_if64([True])
    [[('.1.3.6.1.2.1.1.2.0', '(?!x)x', True)]]
    """
    if if64.need_if64adm(use_if64adm):
        return never_detect
    return if64.HAS_ifHCInOctets


section_plugin = create_snmp_section_plugin(
    name="if64",
    parse_function=if64.parse_if64_if6adm,
    trees=[
        SNMPTree(
            base=if64.BASE_OID,
            oids=if64.END_OIDS,
        ),
    ],
    supersedes=['if'],
    detect_spec=never_detect,  # does not matter what we put here
    rule_dependent_detect_spec=SNMPRuleDependentDetectSpec(
        [RuleSetName('use_if64adm')],
        compute_detect_spec_if64,
    ),
)
add_section_plugin(section_plugin)
assert section_plugin.rule_dependent_detect_spec
for discovery_ruleset in section_plugin.rule_dependent_detect_spec.rulesets:
    add_discovery_ruleset(discovery_ruleset)
# ==================================================================================================

register.check_plugin(
    name="if64",
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
