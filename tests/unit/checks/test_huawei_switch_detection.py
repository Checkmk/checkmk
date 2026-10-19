#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.sectionname import SectionName

# pylint: disable=cmk-module-layer-violation
from cmk.fetchers._snmpscan import _evaluate_snmp_detection as evaluate_snmp_detection

from cmk.base.api.agent_based.register import AgentBasedPlugins

_CHECKS = [
    "huawei_switch_cpu",
    "huawei_switch_fan",
    "huawei_switch_mem",
    "huawei_switch_psu",
    "huawei_switch_stack",
    "huawei_switch_temp",
]


def _detected(plugins: AgentBasedPlugins, check: str, sys_object_id: str) -> list[str]:
    return [
        str(name)
        for name in (SectionName(check), SectionName(f"{check}_huarong"))
        if evaluate_snmp_detection(
            detect_spec=plugins.snmp_sections[name].detect_spec,
            oid_value_getter={".1.3.6.1.2.1.1.2.0": sys_object_id}.get,
        )
    ]


@pytest.mark.parametrize("check", _CHECKS)
@pytest.mark.parametrize(
    "sys_object_id, suffix",
    [
        pytest.param(".1.3.6.1.4.1.2011.2.23.1.2", "", id="huawei enterprise number"),
        pytest.param(".1.3.6.1.4.1.56813.2.23.1.2", "_huarong", id="huarong enterprise number"),
    ],
)
def test_exactly_one_variant_is_detected(
    agent_based_plugins: AgentBasedPlugins, check: str, sys_object_id: str, suffix: str
) -> None:
    assert _detected(agent_based_plugins, check, sys_object_id) == [f"{check}{suffix}"]


@pytest.mark.parametrize("check", _CHECKS)
def test_other_vendor_is_not_detected(agent_based_plugins: AgentBasedPlugins, check: str) -> None:
    assert not _detected(agent_based_plugins, check, ".1.3.6.1.4.1.9.1.1745")


@pytest.mark.parametrize("check", _CHECKS)
def test_huarong_section_feeds_huawei_check(
    agent_based_plugins: AgentBasedPlugins, check: str
) -> None:
    section = agent_based_plugins.snmp_sections[SectionName(f"{check}_huarong")]
    assert str(section.parsed_section_name) == check
