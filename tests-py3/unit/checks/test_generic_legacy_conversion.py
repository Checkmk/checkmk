#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from contextlib import contextmanager

import pytest  # type: ignore[import]

from testlib.base import KNOWN_AUTO_MIGRATION_FAILURES

from cmk.utils.check_utils import section_name_of

import cmk.base.check_api as check_api
import cmk.base.config as config
from cmk.base.api import PluginName
from cmk.base.api.agent_based.register.section_plugins_legacy import _create_snmp_trees
from cmk.base.api.agent_based.register.section_plugins_legacy_scan_function import (
    _explicit_conversions,
    create_detect_spec,
)
from cmk.base.api.agent_based.section_types import AgentSectionPlugin, SNMPSectionPlugin, SNMPTree

pytestmark = pytest.mark.checks


@contextmanager
def known_exceptions(type_, name):
    if (type_, name) not in KNOWN_AUTO_MIGRATION_FAILURES:
        yield
        return

    with pytest.raises(NotImplementedError):
        yield


@pytest.fixture(scope="module", name="_load_all_checks")
def load_all_checks():
    config.load_all_checks(check_api.get_check_api_context)


@pytest.fixture(scope="module", name="snmp_scan_functions", autouse=True)
def _get_snmp_scan_functions(_load_all_checks):
    assert len(config.snmp_scan_functions) > 400  # sanity check
    return config.snmp_scan_functions.copy()


@pytest.fixture(scope="module", name="snmp_info", autouse=True)
def _get_snmp_info(_load_all_checks):
    assert len(config.snmp_info) > 400  # sanity check
    return config.snmp_info.copy()


@pytest.fixture(scope="module", name="check_info", autouse=True)
def _get_check_info(_load_all_checks):
    assert len(config.check_info) > 400  # sanity check
    return config.check_info.copy()


@pytest.fixture(scope="module", name="migrated_agent_sections", autouse=True)
def _get_migrated_agent_sections(_load_all_checks):
    return config.registered_agent_sections.copy()


@pytest.fixture(scope="module", name="migrated_snmp_sections", autouse=True)
def _get_migrated_snmp_sections(_load_all_checks):
    return config.registered_snmp_sections.copy()


@pytest.fixture(scope="module", name="migrated_checks", autouse=True)
def _get_migrated_checks(_load_all_checks):
    return config.registered_check_plugins.copy()


def test_create_section_plugin_from_legacy(check_info, snmp_info, migrated_agent_sections,
                                           migrated_snmp_sections):
    for name, check_info_dict in check_info.items():
        # only test main checks
        if name != section_name_of(name):
            continue

        section_name = PluginName(name)

        with known_exceptions('section', name):
            section = migrated_agent_sections.get(section_name)
            if section is not None:
                assert isinstance(section, AgentSectionPlugin)
            else:
                section = migrated_snmp_sections.get(section_name)
                if section is None:
                    raise NotImplementedError(name)
                assert isinstance(section, SNMPSectionPlugin)

        if section is None:
            continue

        original_parse_function = check_info_dict["parse_function"]
        if original_parse_function is not None:
            assert original_parse_function.__name__ == section.parse_function.__name__


def test_snmp_info_snmp_scan_functions_equal(snmp_info, snmp_scan_functions):
    assert set(snmp_scan_functions) == set(snmp_info)


def test_snmp_tree_tranlation(snmp_info):
    for info_spec in snmp_info.values():
        new_trees, recover_function = _create_snmp_trees(info_spec)
        assert callable(recover_function)  # is tested separately
        assert isinstance(new_trees, list)
        assert all(isinstance(tree, SNMPTree) for tree in new_trees)


def test_scan_function_translation(snmp_scan_functions):
    for name, scan_func in snmp_scan_functions.items():
        if name in (
                # these are already migrated manually:
                "ucd_mem",
                "hr_mem",
        ):
            continue

        assert scan_func is not None

        # make sure we can convert the scan function
        if ('section', name) not in KNOWN_AUTO_MIGRATION_FAILURES:
            _ = create_detect_spec(name, scan_func, [])


@pytest.mark.parametrize("check_name, func_name", [
    ("if64_tplink", "has_ifHCInOctets"),
    ("fsc_subsystems", "_is_fsc_or_windows"),
    ("ucd_processes", "_is_ucd"),
    ("printer_pages", "scan_ricoh_printer"),
    ("fsc_temp", "is_fsc"),
    ("df_netapp32", "is_netapp_filer"),
    ("cisco_cpu", "_has_table_2"),
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
        assert name == section_name_of(name)


def test_exception_required(check_info):
    assert "apc_symmetra_temp" in check_info, (
        "In cmk.base.config is an extra condition for 'apc_symmetra_temp'. "
        "If this test fails, you can remove those two lines along with this test.")


def test_all_checks_migrated(check_info, migrated_checks):
    migrated = set(str(c.name) for c in migrated_checks.values())
    # we don't expect pure section declarations anymore
    true_checks = set(n.replace('.', '_') for n, i in check_info.items() if i['check_function'])
    # we know these fail:
    known_fails = set(name for type_, name in KNOWN_AUTO_MIGRATION_FAILURES if type_ == "check")
    unexpected = migrated & known_fails
    assert not unexpected, "these have been migrated unexpectedly: %r" % (unexpected,)
    failures = true_checks - (migrated | known_fails)
    assert not failures, "failed to migrate: %r" % (failures,)
