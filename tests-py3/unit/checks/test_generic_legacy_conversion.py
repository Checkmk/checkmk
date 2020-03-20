#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from contextlib import contextmanager
import pytest  # type: ignore[import]

from testlib.base import KNOWN_AUTO_MIGRATION_FAILURES
import cmk.base.config as config
import cmk.base.check_api as check_api
import cmk.base.check_utils as check_utils

from cmk.base.api import PluginName

from cmk.base.api.agent_based.section_types import (
    AgentSectionPlugin,
    SNMPSectionPlugin,
    SNMPTree,
)

from cmk.base.api.agent_based.register.section_plugins_legacy_scan_function import (
    create_detect_spec,
    _explicit_conversions,
)

from cmk.base.api.agent_based.register.section_plugins_legacy import (  # pylint: disable=unused-import
    _create_snmp_trees, create_agent_section_plugin_from_legacy,
    create_snmp_section_plugin_from_legacy,
)

pytestmark = pytest.mark.checks

KNOWN_FAILURES = set(plugin_name for _, plugin_name in KNOWN_AUTO_MIGRATION_FAILURES)


@contextmanager
def known_exceptions(name):
    if name not in KNOWN_FAILURES:
        yield
        return

    with pytest.raises(NotImplementedError):
        yield


@pytest.fixture(scope="module", name="_load_all_checks")
def load_all_checks():
    config.load_all_checks(check_api.get_check_api_context)


@pytest.fixture(scope="module", name="snmp_scan_functions")
def _get_snmp_scan_functions(_load_all_checks):
    assert len(config.snmp_scan_functions) > 400  # sanity check
    return config.snmp_scan_functions.copy()


@pytest.fixture(scope="module", name="snmp_info")
def _get_snmp_info(_load_all_checks):
    assert len(config.snmp_info) > 400  # sanity check
    return config.snmp_info.copy()


@pytest.fixture(scope="module", name="check_info")
def _get_check_info(_load_all_checks):
    assert len(config.check_info) > 400  # sanity check
    return config.check_info.copy()


@pytest.fixture(scope="module", name="migrated_agent_sections")
def _get_migrated_agent_sections(_load_all_checks):
    return config.registered_agent_sections.copy()


@pytest.fixture(scope="module", name="migrated_snmp_sections")
def _get_migrated_snmp_sections(_load_all_checks):
    return config.registered_snmp_sections.copy()


def test_create_section_plugin_from_legacy(check_info, snmp_info, migrated_agent_sections,
                                           migrated_snmp_sections):
    for name, check_info_dict in check_info.items():
        # only test main checks
        if name != check_utils.section_name_of(name):
            continue

        section_name = PluginName(name)
        section = None

        if name not in snmp_info:
            section = migrated_agent_sections[section_name]
            assert isinstance(section, AgentSectionPlugin)
        else:
            with known_exceptions(name):
                if section_name not in migrated_snmp_sections:
                    raise NotImplementedError(name)
                section = migrated_snmp_sections[section_name]
                assert isinstance(section, SNMPSectionPlugin)

        if section is None:
            continue

        original_parse_function = check_info_dict["parse_function"]
        if original_parse_function is not None:
            assert original_parse_function.__name__ == section.parse_function.__name__


def test_snmp_info_snmp_scan_functions_equal(snmp_info, snmp_scan_functions):
    # TODO: these don't have scan functions. Fix that! (CMK-4046)
    known_offenders = {'emc_ecs_mem'}
    assert not set(snmp_scan_functions) & known_offenders  # make sure this kept up to date
    assert set(snmp_scan_functions) | known_offenders == set(snmp_info)


def test_snmp_tree_tranlation(snmp_info):
    for info_spec in snmp_info.values():
        new_trees, recover_function = _create_snmp_trees(info_spec)
        assert callable(recover_function)  # is tested separately
        assert isinstance(new_trees, list)
        assert all(isinstance(tree, SNMPTree) for tree in new_trees)


def test_scan_function_translation(snmp_scan_functions):
    for name, scan_func in snmp_scan_functions.items():
        assert scan_func is not None

        # make sure we can convert the scan function
        with known_exceptions(name):
            _ = create_detect_spec(name, scan_func, [])


@pytest.mark.parametrize("check_name, func_name", [
    ("if64_tplink", "has_ifHCInOctets"),
    ("fsc_subsystems", "_is_fsc_or_windows"),
    ("ucd_processes", "_is_ucd"),
    ("printer_pages", "scan_ricoh_printer"),
    ("fsc_temp", "is_fsc"),
    ("df_netapp32", "is_netapp_filer"),
    ("cisco_cpu", "_has_table_8"),
    ("cisco_cpu", "_is_cisco"),
    ("cisco_cpu", "_is_cisco_nexus"),
])
def test_explicit_conversion(check_manager, check_name, func_name):
    scan_func = check_manager.get_check(check_name).context[func_name]
    created = create_detect_spec("unit-test", scan_func, [])
    explicit = _explicit_conversions(scan_func.__name__)
    assert created == explicit


def test_no_subcheck_with_snmp_keywords(snmp_info):
    for name in snmp_info:
        assert name == check_utils.section_name_of(name)
