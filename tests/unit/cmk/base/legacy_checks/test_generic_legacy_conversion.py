#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.checkengine.plugins import AgentBasedPlugins, SectionName
from cmk.discover_plugins import PluginLocation
from tests.unit.mocks_and_helpers import FixPluginLegacy

pytestmark = pytest.mark.checks


def _was_maincheck(lcd: LegacyCheckDefinition) -> bool:
    return lcd.sections is None


def test_create_section_plugin_from_legacy(
    fix_plugin_legacy: FixPluginLegacy, agent_based_plugins: AgentBasedPlugins
) -> None:
    for check_info_dict in fix_plugin_legacy.check_info.values():
        # only test main checks
        if not _was_maincheck(check_info_dict):
            continue

        section_name = SectionName(check_info_dict.name)

        section = (
            agent_based_plugins.agent_sections.get(section_name)
            or agent_based_plugins.snmp_sections[section_name]
        )

        if (original_parse_function := check_info_dict.parse_function) is not None:
            assert original_parse_function.__name__ == section.parse_function.__name__


def test_snmp_info_snmp_detect_equal(fix_plugin_legacy: FixPluginLegacy) -> None:
    for check_info_element in fix_plugin_legacy.check_info.values():
        assert (check_info_element.detect is None) is (check_info_element.fetch is None)


def _defines_section(check_info_element: LegacyCheckDefinition) -> bool:
    if check_info_element.parse_function is not None:
        return True

    assert check_info_element.detect is None
    assert check_info_element.fetch is None
    return False


def _is_section_migrated(name: str, agent_based_plugins: AgentBasedPlugins) -> bool:
    sname = SectionName(name)
    return (
        section := agent_based_plugins.snmp_sections.get(
            sname, agent_based_plugins.agent_sections.get(sname)
        )
    ) is not None and isinstance(section.location, PluginLocation)


def test_sections_definitions_exactly_in_mainchecks(
    fix_plugin_legacy: FixPluginLegacy, agent_based_plugins: AgentBasedPlugins
) -> None:
    """Test where section definitions occur.

    Make sure that sections are defined if and only if it is a main check
    for which no migrated section exists.
    """
    for check_info_element in fix_plugin_legacy.check_info.values():
        if not _was_maincheck(check_info_element):  # subcheck
            assert not _defines_section(check_info_element)
        else:
            assert _is_section_migrated(
                check_info_element.name, agent_based_plugins
            ) is not _defines_section(check_info_element)


def test_all_checks_migrated(
    fix_plugin_legacy: FixPluginLegacy, agent_based_plugins: AgentBasedPlugins
) -> None:
    migrated = {str(name) for name in agent_based_plugins.check_plugins}
    # we don't expect pure section declarations anymore
    true_checks = {lcd.name for lcd in fix_plugin_legacy.check_info.values() if lcd.check_function}
    failures = true_checks - migrated
    assert not failures, f"failed to migrate: {failures!r}"
