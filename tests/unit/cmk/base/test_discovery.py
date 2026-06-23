#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"


import logging
import socket
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import pytest
from pytest import MonkeyPatch

import cmk.utils.paths
from cmk.agent_based.v2 import (
    HostLabel as _APIHostLabel,
)
from cmk.agent_based.v2 import (
    HostLabelGenerator,
    StringTable,
)
from cmk.agent_based.v2 import (
    Service as _APIService,
)
from cmk.base import config
from cmk.base.checkers import (
    CMKFetcher,
    CMKParser,
    DiscoveryPluginMapper,
    HostLabelPluginMapper,
    SectionPluginMapper,
)
from cmk.base.community_app import make_app
from cmk.base.config import ConfigCache
from cmk.base.configlib.checkengine import DiscoveryConfig
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostAddress, HostName, Hosts
from cmk.checkengine.discovery import (
    ABCDiscoveryConfig,
    analyse_cluster_labels,
    AutocheckServiceWithNodes,
    AutochecksStore,
    commandline_discovery,
    discover_host_labels,
    discover_services,
    DiscoveryCheckParameters,
    DiscoveryReport,
    DiscoverySettingFlags,
    DiscoverySettings,
    DiscoveryValueSpecModel,
    find_plugins,
    QualifiedDiscovery,
)
from cmk.checkengine.discovery._autodiscovery import (
    _get_post_discovery_autocheck_services,
    _group_by_transition,
    _make_diff,
    discovery_by_host,
    make_table,
    ServicesByTransition,
    ServicesTable,
    ServicesTableEntry,
)
from cmk.checkengine.discovery._entrypoints.active_check import (
    _check_host_labels,
    _check_service_lists,
)
from cmk.checkengine.discovery._utils.filters import (
    RediscoveryParameters,
    ServiceFilters,
)
from cmk.checkengine.discovery.types import DiscoveredItem
from cmk.checkengine.fetcher import Mode
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.fetcher_utils.trigger import PlainFetcherTrigger
from cmk.checkengine.fetchers import (
    NoSelectedSNMPSections,
    SNMPFetcherConfig,
)
from cmk.checkengine.filecache import FileCacheOptions
from cmk.checkengine.helper_interface import HostKey, SourceType
from cmk.checkengine.parser import AgentRawDataSection, HostSections, NO_SELECTION
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    AgentSectionPlugin,
    AutocheckEntry,
    CheckPluginName,
    FinalCheckResult,
    FinalDiscoveryResult,
    LegacyPluginLocation,
    ParsedSectionName,
    SectionName,
    ServiceID,
)
from cmk.checkengine.plugins import CheckPlugin as InternalCheckPlugin
from cmk.checkengine.sectionparser import (
    ParsedSectionsResolver,
    Provider,
    SectionPlugin,
    SectionsParser,
)
from cmk.checkengine.snmplib import SNMPRawDataElem
from cmk.checkengine.specs.checkresults import ActiveCheckResult
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.rulesets import RuleSetName
from tests.testlib.unit.base_configuration_scenario import Scenario

# ---------------------------------------------------------------------------
# Test-only plug-ins used by the realhost/cluster scenarios.
#
# These minimal fakes mirror just enough of a real section + check plug-in to
# exercise the discovery engine wiring without depending on the product
# plug-in catalogue:
#   * _TEST_SECTION         — agent section that parses [["item", "value"], ...]
#                             rows into a {item: value} dict.
#   * _TEST_LABELS_SECTION  — agent section yielding host labels from
#                             [["label_name", "label_value"], ...] rows.
#   * _TEST_CHECK_PLUGIN    — check plug-in whose discovery function reads a
#                             rule-driven "ignore" list from `params`, so the
#                             host-label-conditional rule branch can be
#                             exercised.
# ---------------------------------------------------------------------------

_TEST_SECTION_NAME = SectionName("test_section")
_TEST_PARSED_NAME = ParsedSectionName("test_section")
_TEST_LABELS_NAME = SectionName("labels")
_TEST_LABELS_PARSED = ParsedSectionName("labels")
_TEST_PLUGIN_NAME = CheckPluginName("test_plugin")
_TEST_DISCOVERY_RULESET = RuleSetName("test_discovery_ruleset")


def _parse_kv(string_table: StringTable) -> Mapping[str, str]:
    return {row[0]: row[1] for row in string_table if len(row) >= 2}


def _host_label_function_test_labels(section: Mapping[str, str]) -> HostLabelGenerator:
    for name, value in section.items():
        yield _APIHostLabel(name, value)


def _no_host_labels(section: Mapping[str, str]) -> HostLabelGenerator:
    yield from ()


def _discovery_function_test(
    params: Mapping[str, object], section: Mapping[str, str]
) -> FinalDiscoveryResult:
    raw_ignore = params.get("ignore") or ()
    assert isinstance(raw_ignore, Sequence)
    for item in section:
        if item not in raw_ignore:
            yield _APIService(item=item)


_TEST_SECTION = AgentSectionPlugin(
    name=_TEST_SECTION_NAME,
    parsed_section_name=_TEST_PARSED_NAME,
    parse_function=_parse_kv,
    host_label_function=_no_host_labels,
    host_label_default_parameters=None,
    host_label_ruleset_name=None,
    host_label_ruleset_type="merged",
    supersedes=set(),
    location=LegacyPluginLocation(file_name="<test>"),
)

_TEST_LABELS_SECTION = AgentSectionPlugin(
    name=_TEST_LABELS_NAME,
    parsed_section_name=_TEST_LABELS_PARSED,
    parse_function=_parse_kv,
    host_label_function=_host_label_function_test_labels,
    host_label_default_parameters=None,
    host_label_ruleset_name=None,
    host_label_ruleset_type="merged",
    supersedes=set(),
    location=LegacyPluginLocation(file_name="<test>"),
)


def _check_function_unused(*args: object, **kw: object) -> FinalCheckResult:
    yield from ()


_TEST_CHECK_PLUGIN = InternalCheckPlugin(
    name=_TEST_PLUGIN_NAME,
    sections=[_TEST_PARSED_NAME],
    service_name="Test %s",
    discovery_function=_discovery_function_test,
    discovery_default_parameters={"ignore": ["item_b"]},
    discovery_ruleset_name=_TEST_DISCOVERY_RULESET,
    discovery_ruleset_type="merged",
    check_function=_check_function_unused,
    check_default_parameters=None,
    check_ruleset_name=None,
    cluster_check_function=None,
    location=LegacyPluginLocation(file_name="<test>"),
)

_TEST_AGENT_SECTIONS: Mapping[SectionName, AgentSectionPlugin] = {
    _TEST_SECTION_NAME: _TEST_SECTION,
    _TEST_LABELS_NAME: _TEST_LABELS_SECTION,
}

_TEST_CHECK_PLUGINS: Mapping[CheckPluginName, InternalCheckPlugin] = {
    _TEST_PLUGIN_NAME: _TEST_CHECK_PLUGIN,
}


def _section_plugin(plugin: AgentSectionPlugin) -> SectionPlugin:
    return SectionPlugin(
        supersedes=plugin.supersedes,
        parsed_section_name=plugin.parsed_section_name,
        parse_function=plugin.parse_function,
    )


@pytest.fixture
def service_table() -> ServicesTable:
    return {
        ServiceID(CheckPluginName("check_plugin_name"), "New Item 1"): ServicesTableEntry(
            transition="new",
            autocheck=DiscoveredItem[AutocheckEntry](
                new=AutocheckEntry(
                    CheckPluginName("check_plugin_name"),
                    "New Item 1",
                    {},
                    {},
                ),
                previous=None,
            ),
            hosts=[],
        ),
        ServiceID(CheckPluginName("check_plugin_name"), "New Item 2"): ServicesTableEntry(
            transition="new",
            autocheck=DiscoveredItem[AutocheckEntry](
                new=AutocheckEntry(
                    CheckPluginName("check_plugin_name"),
                    "New Item 2",
                    {},
                    {},
                ),
                previous=None,
            ),
            hosts=[],
        ),
        ServiceID(CheckPluginName("check_plugin_name"), "Vanished Item 1"): ServicesTableEntry(
            transition="vanished",
            autocheck=DiscoveredItem[AutocheckEntry](
                previous=AutocheckEntry(
                    CheckPluginName("check_plugin_name"),
                    "Vanished Item 1",
                    {},
                    {},
                ),
                new=None,
            ),
            hosts=[],
        ),
        ServiceID(CheckPluginName("check_plugin_name"), "Vanished Item 2"): ServicesTableEntry(
            transition="vanished",
            autocheck=DiscoveredItem[AutocheckEntry](
                previous=AutocheckEntry(
                    CheckPluginName("check_plugin_name"),
                    "Vanished Item 2",
                    {},
                    {},
                ),
                new=None,
            ),
            hosts=[],
        ),
    }


@pytest.fixture
def grouped_services() -> ServicesByTransition:
    return {
        "new": [
            AutocheckServiceWithNodes(
                DiscoveredItem[AutocheckEntry](
                    new=AutocheckEntry(
                        CheckPluginName("check_plugin_name"),
                        "New Item 1",
                        {},
                        {},
                    ),
                    previous=None,
                ),
                [],
            ),
            AutocheckServiceWithNodes(
                DiscoveredItem[AutocheckEntry](
                    new=AutocheckEntry(
                        CheckPluginName("check_plugin_name"),
                        "New Item 2",
                        {},
                        {},
                    ),
                    previous=None,
                ),
                [],
            ),
        ],
        "vanished": [
            AutocheckServiceWithNodes(
                DiscoveredItem[AutocheckEntry](
                    previous=AutocheckEntry(
                        CheckPluginName("check_plugin_name"),
                        "Vanished Item 1",
                        {},
                        {},
                    ),
                    new=None,
                ),
                [],
            ),
            AutocheckServiceWithNodes(
                DiscoveredItem[AutocheckEntry](
                    previous=AutocheckEntry(
                        CheckPluginName("check_plugin_name"),
                        "Vanished Item 2",
                        {},
                        {},
                    ),
                    new=None,
                ),
                [],
            ),
        ],
    }


def test__group_by_transition(
    service_table: ServicesTable, grouped_services: ServicesByTransition
) -> None:
    assert _group_by_transition(service_table) == grouped_services


@pytest.mark.parametrize(
    "mode, parameters_rediscovery, result_new_item_names, result_counts",
    [
        # No params
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=False,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {},
            ["New Item 1", "New Item 2", "Vanished Item 1", "Vanished Item 2"],
            (2, 2, 0),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {},
            ["New Item 1", "New Item 2"],
            (2, 0, 2),
        ),
        # TODO For "refresh" we currently do not "remove vanished services".
        # What the code rather does is: It does not load the existing services.
        # Then there are no "vanished services", they just disappeared as if
        # they never existed. It's the code that needs
        # fixing...
        # https://review.lan.tribe29.com/c/check_mk/+/67447
        # grep for '67447' to find the other 5 places in this test
        (
            (
                "update_everything",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=True,
                    update_changed_service_parameters=True,
                ),
            ),
            {},
            ["New Item 1", "New Item 2"],
            (2, 0, 2),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=False,
                    remove_vanished_services=True,
                    update_host_labels=False,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {},
            [],
            (0, 0, 2),
        ),
        # New services
        # Whitelist
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=False,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_whitelist": ["^Test Description New Item 1"]},
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_whitelist": ["^Test Description New Item 1"]},
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            (
                "update_everything",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=True,
                    update_changed_service_parameters=True,
                ),
            ),
            {"service_whitelist": ["^Test Description New Item 1"]},
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=False,
                    remove_vanished_services=True,
                    update_host_labels=False,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_whitelist": ["^Test Description New Item 1"]},
            ["Vanished Item 1", "Vanished Item 2"],
            (0, 2, 0),
        ),
        # Blacklist
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=False,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_blacklist": ["^Test Description New Item 1"]},
            ["New Item 2", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_blacklist": ["^Test Description New Item 1"]},
            ["New Item 2"],
            (1, 0, 2),
        ),
        # TODO 67447
        (
            (
                "update_everything",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=True,
                    update_changed_service_parameters=True,
                ),
            ),
            {"service_blacklist": ["^Test Description New Item 1"]},
            ["New Item 2"],
            (1, 0, 2),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=False,
                    remove_vanished_services=True,
                    update_host_labels=False,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_blacklist": ["^Test Description New Item 1"]},
            [],
            (0, 0, 2),
        ),
        # White-/blacklist
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=False,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            (
                "update_everything",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=True,
                    update_changed_service_parameters=True,
                ),
            ),
            {
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=False,
                    remove_vanished_services=True,
                    update_host_labels=False,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
            ["Vanished Item 1", "Vanished Item 2"],
            (0, 2, 0),
        ),
        # Service vanished
        # Whitelist
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=False,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_whitelist": ["^Test Description Vanished Item 1"]},
            ["Vanished Item 1", "Vanished Item 2"],
            (0, 2, 0),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_whitelist": ["^Test Description Vanished Item 1"]},
            ["Vanished Item 2"],
            (0, 1, 1),
        ),
        # TODO 67447
        (
            (
                "update_everything",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=True,
                    update_changed_service_parameters=True,
                ),
            ),
            {"service_whitelist": ["^Test Description Vanished Item 1"]},
            ["Vanished Item 2"],
            (0, 1, 1),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=False,
                    remove_vanished_services=True,
                    update_host_labels=False,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_whitelist": ["^Test Description Vanished Item 1"]},
            ["Vanished Item 2"],
            (0, 1, 1),
        ),
        # Blacklist
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=False,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_blacklist": ["^Test Description Vanished Item 1"]},
            ["New Item 1", "New Item 2", "Vanished Item 1", "Vanished Item 2"],
            (2, 2, 0),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_blacklist": ["^Test Description Vanished Item 1"]},
            ["New Item 1", "New Item 2", "Vanished Item 1"],
            (2, 1, 1),
        ),
        # TODO 67447
        (
            (
                "update_everything",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=True,
                    update_changed_service_parameters=True,
                ),
            ),
            {"service_blacklist": ["^Test Description Vanished Item 1"]},
            ["New Item 1", "New Item 2", "Vanished Item 1"],
            (2, 1, 1),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=False,
                    remove_vanished_services=True,
                    update_host_labels=False,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {"service_blacklist": ["^Test Description Vanished Item 1"]},
            ["Vanished Item 1"],
            (0, 1, 1),
        ),
        # White-/blacklist
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=False,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {
                "service_whitelist": ["^Test Description Vanished Item 1"],
                "service_blacklist": ["^Test Description Vanished Item 2"],
            },
            ["Vanished Item 1", "Vanished Item 2"],
            (0, 2, 0),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {
                "service_whitelist": ["^Test Description Vanished Item 1"],
                "service_blacklist": ["^Test Description Vanished Item 2"],
            },
            ["Vanished Item 2"],
            (0, 1, 1),
        ),
        # TODO 67447
        (
            (
                "update_everything",
                DiscoverySettingFlags(
                    add_new_services=True,
                    remove_vanished_services=True,
                    update_host_labels=True,
                    update_changed_service_labels=True,
                    update_changed_service_parameters=True,
                ),
            ),
            {
                "service_whitelist": ["^Test Description Vanished Item 1"],
                "service_blacklist": ["^Test Description Vanished Item 2"],
            },
            ["Vanished Item 2"],
            (0, 1, 1),
        ),
        (
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=False,
                    remove_vanished_services=True,
                    update_host_labels=False,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
            {
                "service_whitelist": ["^Test Description Vanished Item 1"],
                "service_blacklist": ["^Test Description Vanished Item 2"],
            },
            ["Vanished Item 2"],
            (0, 1, 1),
        ),
    ],
)
def test__get_post_discovery_services(
    grouped_services: ServicesByTransition,
    mode: DiscoveryValueSpecModel,
    parameters_rediscovery: RediscoveryParameters,
    result_new_item_names: list[str],
    result_counts: tuple[int, int, int],
) -> None:
    result = DiscoveryReport()

    service_filters = ServiceFilters.from_settings(parameters_rediscovery)

    new_item_names = [
        entry.service.newer.item or ""
        for entry in _get_post_discovery_autocheck_services(
            HostName("hostname"),
            grouped_services,
            service_filters,
            result,
            get_service_description=lambda hn, entry: f"Test Description {entry.item}",
            settings=DiscoverySettings.from_vs(mode),
            keep_clustered_vanished_services=True,
        ).values()
    ]

    count_new, count_kept, count_removed = result_counts

    assert sorted(new_item_names) == sorted(result_new_item_names)
    assert result.services.new == count_new
    assert result.services.kept == count_kept
    assert result.services.removed == count_removed


def test__get_post_discovery_services_drops_ignored_from_autochecks() -> None:
    """Services matched by a 'Disabled services' rule (transition 'ignored') must not be
    persisted to the autochecks file -- only monitored services are supposed to be there
    (see werk 19800).  They are still counted as 'kept' so reporting/diff stays sensible.
    """
    services_by_transition: ServicesByTransition = {
        "ignored": [
            AutocheckServiceWithNodes(
                DiscoveredItem[AutocheckEntry](
                    new=AutocheckEntry(
                        CheckPluginName("check_plugin_name"),
                        "Ignored Item",
                        {},
                        {},
                    ),
                    previous=AutocheckEntry(
                        CheckPluginName("check_plugin_name"),
                        "Ignored Item",
                        {},
                        {},
                    ),
                ),
                [],
            ),
        ],
    }
    result = DiscoveryReport()

    post_discovery = _get_post_discovery_autocheck_services(
        HostName("hostname"),
        services_by_transition,
        ServiceFilters.accept_all(),
        result,
        get_service_description=lambda hn, entry: f"Test Description {entry.item}",
        settings=DiscoverySettings(
            update_host_labels=True,
            add_new_services=True,
            remove_vanished_services=True,
            update_changed_service_labels=True,
            update_changed_service_parameters=True,
        ),
        keep_clustered_vanished_services=True,
    )

    assert post_discovery == {}
    assert result.services.kept == 1
    assert result.services.removed == 0


def _get_params(rediscovery: RediscoveryParameters) -> DiscoveryCheckParameters:
    return DiscoveryCheckParameters(
        commandline_only=False,
        check_interval=60,
        severity_new_services=1,
        severity_vanished_services=0,
        severity_changed_service_labels=0,
        severity_changed_service_params=1,
        severity_new_host_labels=0,
        rediscovery=rediscovery,
    )


@pytest.mark.parametrize(
    "parameters, result_need_rediscovery",
    [
        (_get_params({}), False),
        # New services
        # Whitelist
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=False,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=False,
                            remove_vanished_services=True,
                            update_host_labels=False,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description New Item 1"],
                }
            ),
            False,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "update_everything",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=True,
                            update_changed_service_parameters=True,
                        ),
                    ),
                    "service_whitelist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        # Blacklist
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=False,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_blacklist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=False,
                            remove_vanished_services=True,
                            update_host_labels=False,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_blacklist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_blacklist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "update_everything",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=True,
                            update_changed_service_parameters=True,
                        ),
                    ),
                    "service_blacklist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        # White-/blacklist
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=False,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description New Item 1"],
                    "service_blacklist": ["^Test Description New Item 2"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=False,
                            remove_vanished_services=True,
                            update_host_labels=False,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description New Item 1"],
                    "service_blacklist": ["^Test Description New Item 2"],
                }
            ),
            False,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description New Item 1"],
                    "service_blacklist": ["^Test Description New Item 2"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "update_everything",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=True,
                            update_changed_service_parameters=True,
                        ),
                    ),
                    "service_whitelist": ["^Test Description New Item 1"],
                    "service_blacklist": ["^Test Description New Item 2"],
                }
            ),
            True,
        ),
        # Service vanished
        # Whitelist
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=False,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                }
            ),
            False,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=False,
                            remove_vanished_services=True,
                            update_host_labels=False,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "update_everything",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=True,
                            update_changed_service_parameters=True,
                        ),
                    ),
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        # Blacklist
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=False,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_blacklist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=False,
                            remove_vanished_services=True,
                            update_host_labels=False,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_blacklist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_blacklist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "update_everything",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=True,
                            update_changed_service_parameters=True,
                        ),
                    ),
                    "service_blacklist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        # White-/blacklist
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=False,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                    "service_blacklist": ["^Test Description Vanished Item 2"],
                }
            ),
            False,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=False,
                            remove_vanished_services=True,
                            update_host_labels=False,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                    "service_blacklist": ["^Test Description Vanished Item 2"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "custom",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=False,
                            update_changed_service_parameters=False,
                        ),
                    ),
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                    "service_blacklist": ["^Test Description Vanished Item 2"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": (
                        "update_everything",
                        DiscoverySettingFlags(
                            add_new_services=True,
                            remove_vanished_services=True,
                            update_host_labels=True,
                            update_changed_service_labels=True,
                            update_changed_service_parameters=True,
                        ),
                    ),
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                    "service_blacklist": ["^Test Description Vanished Item 2"],
                }
            ),
            True,
        ),
    ],
)
def test__check_service_table(
    grouped_services: ServicesByTransition,
    parameters: DiscoveryCheckParameters,
    result_need_rediscovery: bool,
) -> None:
    rediscovery_parameters = parameters.rediscovery.copy()
    discovery_mode = DiscoverySettings.from_vs(
        rediscovery_parameters.pop(
            "mode",
            (
                "custom",
                DiscoverySettingFlags(
                    add_new_services=False,
                    remove_vanished_services=False,
                    update_host_labels=False,
                    update_changed_service_labels=False,
                    update_changed_service_parameters=False,
                ),
            ),
        )
    )
    results, need_rediscovery = _check_service_lists(
        host_name=HostName("hostname"),
        services_by_transition=grouped_services,
        params=parameters,
        service_filters=ServiceFilters.from_settings(rediscovery_parameters),
        get_service_description=lambda hn, entry: f"Test Description {entry.item}",
        discovery_mode=discovery_mode,
    )

    assert results == [
        ActiveCheckResult(
            state=0,
            summary="",
            details=[
                "Service unmonitored: check_plugin_name: Test Description New Item 1",
            ],
        ),
        ActiveCheckResult(
            state=0,
            summary="",
            details=[
                "Service unmonitored: check_plugin_name: Test Description New Item 2",
            ],
        ),
        ActiveCheckResult(state=1, summary="Services unmonitored: 2 (check_plugin_name: 2)"),
        ActiveCheckResult(
            state=0,
            summary="",
            details=[
                "Service vanished: check_plugin_name: Test Description Vanished Item 1",
            ],
        ),
        ActiveCheckResult(
            state=0,
            summary="",
            details=[
                "Service vanished: check_plugin_name: Test Description Vanished Item 2",
            ],
        ),
        ActiveCheckResult(state=0, summary="Services vanished: 2 (check_plugin_name: 2)"),
    ]
    assert need_rediscovery == result_need_rediscovery


def test__check_host_labels_up_to_date() -> None:
    assert _check_host_labels(
        QualifiedDiscovery(
            preexisting=[
                HostLabel("this", "unchanged", SectionName("labels")),
                HostLabel("that", "unchanged", SectionName("my_section")),
                HostLabel("anotherone", "thesame", SectionName("labels")),
            ],
            current=[
                HostLabel("this", "unchanged", SectionName("labels")),
                HostLabel("that", "unchanged", SectionName("my_section")),
                HostLabel("anotherone", "thesame", SectionName("labels")),
            ],
        ),
        1,
        DiscoverySettings(
            add_new_services=False,
            remove_vanished_services=False,
            update_host_labels=True,
            update_changed_service_labels=False,
            update_changed_service_parameters=False,
        ),
    ) == ([ActiveCheckResult(state=0, summary="Host labels: all up to date")], False)


def test__check_host_labels_changed() -> None:
    assert _check_host_labels(
        QualifiedDiscovery(
            preexisting=[
                HostLabel("this", "unchanged", SectionName("labels")),
                HostLabel("that", "changes", SectionName("my_section")),
                HostLabel("anotherone", "vanishes", SectionName("my_section")),
            ],
            current=[
                HostLabel("this", "unchanged", SectionName("labels")),
                HostLabel("that", "yay-new-value", SectionName("my_section")),
                HostLabel("yetanotherone", "isnew", SectionName("labels")),
            ],
        ),
        1,
        DiscoverySettings(
            add_new_services=False,
            remove_vanished_services=False,
            update_host_labels=True,
            update_changed_service_labels=False,
            update_changed_service_parameters=False,
        ),
    ) == (
        [
            ActiveCheckResult(
                state=1,
                summary="New host labels: 2 (my_section: 1, labels: 1)",
                details=[
                    "New host label: my_section: that:yay-new-value",
                    "New host label: labels: yetanotherone:isnew",
                ],
            ),
            ActiveCheckResult(
                state=0,
                summary="Vanished host labels: 2 (my_section: 2)",
                details=[
                    "Vanished host label: my_section: that:changes",
                    "Vanished host label: my_section: anotherone:vanishes",
                ],
            ),
        ],
        True,
    )


def test__find_candidates(monkeypatch: MonkeyPatch) -> None:
    Scenario().apply(monkeypatch)

    def _trivial(name: str) -> SectionPlugin:
        return SectionPlugin(
            supersedes=set(),
            parsed_section_name=ParsedSectionName(name),
            parse_function=lambda x: x,
        )

    providers = {
        HostKey(HostName("test_node"), SourceType.HOST): (
            ParsedSectionsResolver(
                SectionsParser(
                    host_sections=HostSections[AgentRawDataSection](
                        {
                            SectionName("agent_only"): [["x"]],  # host only
                            SectionName("shared"): [["x"]],  # host & mgmt
                        }
                    ),
                    host_name=HostName("test_node"),
                    error_handling=lambda *args, **kw: "error",
                ),
                section_plugins={
                    SectionName("agent_only"): _trivial("agent_only"),
                    SectionName("shared"): _trivial("shared"),
                },
            )
        ),
        HostKey(HostName("test_node"), SourceType.MANAGEMENT): (
            ParsedSectionsResolver(
                SectionsParser(
                    host_sections=HostSections[Mapping[SectionName, SNMPRawDataElem]](
                        {
                            SectionName("shared"): [[["x"]]],  # host & mgmt
                            SectionName("snmp_only"): [[["x"]]],  # mgmt only
                            SectionName("mgmt_prefixed"): [[["x"]]],  # already mgmt_-prefixed
                        }
                    ),
                    host_name=HostName("test_node"),
                    error_handling=lambda *args, **kw: "error",
                ),
                section_plugins={
                    SectionName("shared"): _trivial("shared"),
                    SectionName("snmp_only"): _trivial("snmp_only"),
                    SectionName("mgmt_prefixed"): _trivial("mgmt_prefixed"),
                },
            )
        ),
    }

    # Synthetic plug-in catalog covering the algorithm's branches: a host-only
    # plug-in, a plug-in whose section is provided on both sides, a plug-in whose
    # section only appears on the management board, and a plug-in that is already
    # management-prefixed.
    candidates: list[tuple[CheckPluginName, list[ParsedSectionName]]] = [
        (CheckPluginName("uses_agent_only"), [ParsedSectionName("agent_only")]),
        (CheckPluginName("uses_shared"), [ParsedSectionName("shared")]),
        (CheckPluginName("uses_snmp_only"), [ParsedSectionName("snmp_only")]),
        (
            CheckPluginName("mgmt_uses_mgmt_prefixed"),
            [ParsedSectionName("mgmt_prefixed")],
        ),
    ]
    expected_plugins = {
        # host side: non-mgmt plug-ins whose sections are available on the host
        CheckPluginName("uses_agent_only"),
        CheckPluginName("uses_shared"),
        # mgmt side: every plug-in whose sections are available on mgmt, with the
        # mgmt_ prefix added (idempotently)
        CheckPluginName("mgmt_uses_shared"),
        CheckPluginName("mgmt_uses_snmp_only"),
        CheckPluginName("mgmt_uses_mgmt_prefixed"),
    }

    assert find_plugins(providers, candidates) == expected_plugins


_EXPECTED_SERVICES: Mapping[ServiceID, Mapping[str, str]] = {
    ServiceID(_TEST_PLUGIN_NAME, "item_a"): {},
}

_EXPECTED_HOST_LABELS = [
    HostLabel("cmk/check_mk_server", "yes", _TEST_LABELS_NAME),
]


class _EmptyDiscoveryConfig(ABCDiscoveryConfig):
    def __call__(
        self, host_name: object, rule_set_name: object, rule_set_type: str
    ) -> Mapping[str, object] | Sequence[Mapping[str, object]]:
        return [] if rule_set_type == "all" else {}


@pytest.mark.usefixtures("patch_omd_site")
def test_commandline_discovery(monkeypatch: MonkeyPatch) -> None:
    """End-to-end test of the commandline_discovery() entrypoint with a
    minimal fake plug-in set. Beyond the discovered service result, this is
    the only test in the module that covers:

    1. The commandline_discovery() entrypoint — i.e. what ``cmk -I`` calls.
       Other tests in this file call ``discover_services()`` /
       ``discover_host_labels()`` directly.
    2. Parser + fetcher wiring — :class:`CMKParser` + :class:`CMKFetcher`
       constructed from a real :class:`ConfigCache` with the full
       dependency graph (factories, secrets, IP-lookup callbacks, fetcher
       trigger, etc.).
    3. The ``datasource_programs`` → cached file → fetcher path.
    4. Persistence side-effects — :meth:`AutochecksStore.read` and
       :meth:`DiscoveredHostLabelsStore.load` after the pipeline runs.
    """
    testhost = HostName("test-host")
    ts = Scenario()
    ts.add_host(testhost, ipaddress=HostAddress("127.0.0.1"))
    ts.set_ruleset(
        "datasource_programs",
        [
            {
                "condition": {"host_name": [testhost]},
                "id": "test-datasource",
                "value": f"cat {cmk.utils.paths.tcp_cache_dir}/<HOST>",
            }
        ],
    )
    cache_path = cmk.utils.paths.tcp_cache_dir / testhost
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        "<<<test_section>>>\nitem_a ok\nitem_b ok\n<<<labels>>>\ncmk/check_mk_server yes\n"
    )
    loading_result = ts.apply(monkeypatch)
    config_cache = loading_result.config_cache

    plugins = AgentBasedPlugins(
        agent_sections=_TEST_AGENT_SECTIONS,
        snmp_sections={},
        check_plugins=_TEST_CHECK_PLUGINS,
        inventory_plugins={},
        errors=(),
    )

    file_cache_options = FileCacheOptions()
    parser = CMKParser(
        config.make_parser_config(
            loading_result.loaded_config,
            config_cache.ruleset_matcher,
            config_cache.label_manager,
            ip_address_of=config_cache.primary_ip_address_of,
        ),
        selected_sections=NO_SELECTION,
        keep_outdated=file_cache_options.keep_outdated,
        logger=logging.getLogger("tests"),
    )
    service_name_config = config_cache.make_passive_service_name_config(
        make_final_service_name_config(loading_result.loaded_config, config_cache.ruleset_matcher)
    )
    app = make_app()
    fetcher = CMKFetcher(
        config_cache,
        get_relay_id=lambda hn: None,
        make_trigger=lambda hn: PlainFetcherTrigger(Path("/")),
        factory=config_cache.fetcher_factory(
            config_cache.make_service_configurer({}, service_name_config),
            ip_lookup=lambda *a: HostAddress(""),
            service_name_config=service_name_config,
            enforced_services_table=lambda hn: {},
            snmp_fetcher_config=SNMPFetcherConfig(
                on_error=OnError.RAISE,
                missing_sys_description=lambda host_name: False,
                selected_sections=NoSelectedSNMPSections(),
                backend_override=None,
                base_path=Path("/"),
                relative_stored_walk_path=Path("dev/null"),
                relative_walk_cache_path=Path("dev/null"),
                relative_section_cache_path=Path("dev/null"),
                caching_config=lambda host_name: {},
            ),
        ),
        plugins=plugins,
        clusters=loading_result.hosts_config.clusters,
        default_address_family=lambda *a: socket.AddressFamily.AF_INET,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=False,
        get_ip_stack_config=lambda *a: IPStackConfig.IPv4,
        ip_address_of=lambda *a: HostAddress(""),
        ip_address_of_mandatory=lambda *a: HostAddress(""),
        ip_address_of_mgmt=lambda *a: HostAddress(""),
        mode=Mode.DISCOVERY,
        simulation_mode=True,
        secrets_config_relay=AdHocSecrets(
            path=Path("/pw/relay"),
            secrets={},
        ),
        secrets_config_site=StoredSecrets(
            path=Path("/pw/store"),
            secrets={},
        ),
        metric_backend_fetcher_factory=lambda hn: app.make_metric_backend_fetcher(
            hn,
            config_cache.explicit_host_attributes,
            config_cache.check_mk_check_interval,
        ),
    )

    commandline_discovery(
        host_name=testhost,
        clear_ruleset_matcher_caches=config_cache.ruleset_matcher.clear_caches,
        parser=parser,
        fetcher=fetcher,
        section_plugins=SectionPluginMapper(_TEST_AGENT_SECTIONS),
        section_error_handling=lambda *args, **kw: "error",
        host_label_plugins=HostLabelPluginMapper(
            discovery_config=_EmptyDiscoveryConfig(),
            sections=_TEST_AGENT_SECTIONS,
        ),
        plugins=DiscoveryPluginMapper(
            discovery_config=_EmptyDiscoveryConfig(),
            check_plugins=_TEST_CHECK_PLUGINS,
        ),
        run_plugin_names=EVERYTHING,
        ignore_plugin=lambda *args, **kw: False,
        arg_only_new=False,
        on_error=OnError.RAISE,
        autochecks_dir=cmk.utils.paths.autochecks_dir,
        discovered_host_labels_dir=cmk.utils.paths.discovered_host_labels_dir,
    )

    entries = AutochecksStore(testhost, cmk.utils.paths.autochecks_dir).read()
    found = {e.id(): e.service_labels for e in entries}
    assert found == _EXPECTED_SERVICES

    store = DiscoveredHostLabelsStore(testhost, cmk.utils.paths.discovered_host_labels_dir)
    assert store.load() == _EXPECTED_HOST_LABELS


class RealHostScenario(NamedTuple):
    hostname: HostName
    config_cache: ConfigCache
    providers: Mapping[HostKey, Provider]

    @property
    def host_key(self) -> HostKey:
        return HostKey(self.hostname, SourceType.HOST)

    @property
    def host_key_mgmt(self) -> HostKey:
        return HostKey(self.hostname, SourceType.MANAGEMENT)


@pytest.fixture(name="realhost_scenario")
def _realhost_scenario(monkeypatch: MonkeyPatch) -> RealHostScenario:
    hostname = HostName("test-realhost")
    ts = Scenario()
    ts.add_host(hostname, ipaddress=HostAddress("127.0.0.1"))
    config_cache = ts.apply(monkeypatch).config_cache

    DiscoveredHostLabelsStore(hostname, cmk.utils.paths.discovered_host_labels_dir).save(
        [
            HostLabel("existing_label", "bar", SectionName("foo")),
            HostLabel("another_label", "true", _TEST_LABELS_NAME),
        ]
    )

    providers = {
        HostKey(hostname=hostname, source_type=SourceType.HOST): (
            ParsedSectionsResolver(
                SectionsParser(
                    host_sections=HostSections[AgentRawDataSection](
                        sections={
                            _TEST_LABELS_NAME: [["cmk/check_mk_server", "yes"]],
                            _TEST_SECTION_NAME: [["item_a", "ok"], ["item_b", "ok"]],
                        }
                    ),
                    host_name=hostname,
                    error_handling=lambda *args, **kw: "error",
                ),
                section_plugins={
                    _TEST_LABELS_NAME: _section_plugin(_TEST_LABELS_SECTION),
                    _TEST_SECTION_NAME: _section_plugin(_TEST_SECTION),
                },
            )
        )
    }

    return RealHostScenario(hostname, config_cache, providers)


class ClusterScenario(NamedTuple):
    parent: HostName
    config_cache: ConfigCache
    hosts_config: Hosts
    providers: Mapping[HostKey, Provider]
    node1_hostname: HostName
    node2_hostname: HostName


@pytest.fixture(name="cluster_scenario")
def _cluster_scenario(monkeypatch: pytest.MonkeyPatch) -> ClusterScenario:
    hostname = HostName("test-clusterhost")
    node1_hostname = HostName("test-node1")
    node2_hostname = HostName("test-node2")

    ts = Scenario()
    ts.add_host(node1_hostname)
    ts.add_host(node2_hostname)
    ts.add_cluster(hostname, nodes=[node1_hostname, node2_hostname])
    ts.set_ruleset(
        "clustered_services",
        [
            {
                "id": "01",
                "condition": {
                    "service_description": [{"$regex": "Test "}],
                    "host_name": [node1_hostname],
                },
                "value": True,
            }
        ],
    )
    loading_result = ts.apply(monkeypatch)
    config_cache = loading_result.config_cache

    DiscoveredHostLabelsStore(node1_hostname, cmk.utils.paths.discovered_host_labels_dir).save(
        [HostLabel("node1_existing_label", "true", SectionName("node1_plugin"))]
    )

    providers = {
        HostKey(hostname=node1_hostname, source_type=SourceType.HOST): (
            ParsedSectionsResolver(
                SectionsParser(
                    host_sections=HostSections[AgentRawDataSection](
                        sections={
                            _TEST_LABELS_NAME: [["cmk/check_mk_server", "yes"]],
                            _TEST_SECTION_NAME: [["item_a", "ok"], ["item_b", "ok"]],
                        }
                    ),
                    host_name=node1_hostname,
                    error_handling=lambda *args, **kw: "error",
                ),
                section_plugins={
                    _TEST_LABELS_NAME: _section_plugin(_TEST_LABELS_SECTION),
                    _TEST_SECTION_NAME: _section_plugin(_TEST_SECTION),
                },
            )
        ),
        HostKey(hostname=node2_hostname, source_type=SourceType.HOST): (
            ParsedSectionsResolver(
                SectionsParser(
                    host_sections=HostSections[AgentRawDataSection](
                        sections={
                            _TEST_LABELS_NAME: [["node2_live_label", "true"]],
                            _TEST_SECTION_NAME: [["item_a", "ok"], ["item_b", "ok"]],
                        }
                    ),
                    host_name=node2_hostname,
                    error_handling=lambda *args, **kw: "error",
                ),
                section_plugins={
                    _TEST_LABELS_NAME: _section_plugin(_TEST_LABELS_SECTION),
                    _TEST_SECTION_NAME: _section_plugin(_TEST_SECTION),
                },
            )
        ),
    }

    return ClusterScenario(
        hostname,
        config_cache,
        loading_result.hosts_config,
        providers,
        node1_hostname,
        node2_hostname,
    )


class ExpectedDiscoveryResultOnRealhost(NamedTuple):
    expected_vanished_host_labels: Sequence[HostLabel]
    expected_old_host_labels: Sequence[HostLabel]
    expected_new_host_labels: Sequence[HostLabel]
    expected_kept_labels: Sequence[HostLabel]


class ExpectedDiscoveryResultOnCluster(NamedTuple):
    expected_vanished_host_labels: Sequence[HostLabel]
    expected_old_host_labels: Sequence[HostLabel]
    expected_new_host_labels: Sequence[HostLabel]
    expected_kept_labels: Mapping[HostName, Sequence[HostLabel]]


class DiscoveryTestCase(NamedTuple):
    load_labels: bool
    only_host_labels: bool
    expected_services: set[tuple[CheckPluginName, str]]
    on_realhost: ExpectedDiscoveryResultOnRealhost
    on_cluster: ExpectedDiscoveryResultOnCluster


@pytest.mark.parametrize(
    "host_labels, expected_services",
    [
        ((), {ServiceID(_TEST_PLUGIN_NAME, "item_a")}),
        (
            (HostLabel("cmk/check_mk_server", "yes", _TEST_LABELS_NAME),),
            {
                ServiceID(_TEST_PLUGIN_NAME, "item_a"),
                ServiceID(_TEST_PLUGIN_NAME, "item_b"),
            },
        ),
    ],
)
def test__discovery_considers_host_labels(
    host_labels: tuple[HostLabel],
    expected_services: set[ServiceID],
    realhost_scenario: RealHostScenario,
) -> None:
    # this takes the detour via ruleset matcher :-(
    DiscoveredHostLabelsStore(
        realhost_scenario.hostname, cmk.utils.paths.discovered_host_labels_dir
    ).save(host_labels)

    # unpack for readability
    host_name = realhost_scenario.hostname
    config_cache = realhost_scenario.config_cache
    providers = realhost_scenario.providers

    # The rule overrides the plug-in's default "ignore" list (which excludes
    # "item_b") with an empty list, but only when the host carries the
    # cmk/check_mk_server:yes label.
    plugins = DiscoveryPluginMapper(
        discovery_config=DiscoveryConfig(
            config_cache.ruleset_matcher,
            config_cache.label_manager.labels_of_host,
            rules={
                _TEST_DISCOVERY_RULESET: [
                    {
                        "id": "nobody-cares-about-the-id-in-this-test",
                        "value": {"ignore": []},
                        "condition": {
                            "host_label_groups": [("and", [("and", "cmk/check_mk_server:yes")])]
                        },
                    }
                ],
            },
        ),
        check_plugins=_TEST_CHECK_PLUGINS,
    )
    plugin_names = find_plugins(
        providers,
        [(plugin_name, plugin.sections) for plugin_name, plugin in plugins.items()],
    )

    assert {
        entry.id()
        for entry in discover_services(
            host_name,
            plugin_names,
            providers=providers,
            plugins=plugins,
            on_error=OnError.RAISE,
        )
    } == expected_services


_discovery_test_cases = [
    # do discovery: only_new == True
    # discover on host: mode != "remove"
    DiscoveryTestCase(
        load_labels=True,
        only_host_labels=False,
        expected_services={
            (_TEST_PLUGIN_NAME, "item_a"),
        },
        on_realhost=ExpectedDiscoveryResultOnRealhost(
            expected_vanished_host_labels=[
                HostLabel("existing_label", "bar", SectionName("foo")),
                HostLabel("another_label", "true", SectionName("labels")),
            ],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
            ],
            expected_kept_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
            ],
        ),
        on_cluster=ExpectedDiscoveryResultOnCluster(
            expected_vanished_host_labels=[
                HostLabel(
                    "node1_existing_label",
                    "true",
                    plugin_name=SectionName("node1_plugin"),
                )
            ],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                HostLabel("node2_live_label", "true", SectionName("labels")),
            ],
            expected_kept_labels={
                HostName("test-clusterhost"): [
                    HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                    HostLabel("node2_live_label", "true", SectionName("labels")),
                ],
                HostName("test-node1"): [
                    HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                ],
                HostName("test-node2"): [
                    HostLabel("node2_live_label", "true", SectionName("labels")),
                ],
            },
        ),
    ),
    # do discovery: only_new == False
    DiscoveryTestCase(
        load_labels=False,
        only_host_labels=False,
        expected_services={
            (_TEST_PLUGIN_NAME, "item_a"),
        },
        on_realhost=ExpectedDiscoveryResultOnRealhost(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
            ],
            expected_kept_labels=[HostLabel("cmk/check_mk_server", "yes", SectionName("labels"))],
        ),
        on_cluster=ExpectedDiscoveryResultOnCluster(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                HostLabel("node2_live_label", "true", SectionName("labels")),
            ],
            expected_kept_labels={
                HostName("test-clusterhost"): [
                    HostLabel("cmk/check_mk_server", "yes", plugin_name=SectionName("labels")),
                    HostLabel("node2_live_label", "true", plugin_name=SectionName("labels")),
                ],
                HostName("test-node1"): [
                    HostLabel("cmk/check_mk_server", "yes", SectionName("labels"))
                ],
                HostName("test-node2"): [
                    HostLabel("node2_live_label", "true", SectionName("labels"))
                ],
            },
        ),
    ),
    # discover on host: mode == "only-host-labels"
    # Only discover host labels
    DiscoveryTestCase(
        load_labels=False,
        only_host_labels=True,
        expected_services=set(),
        on_realhost=ExpectedDiscoveryResultOnRealhost(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
            ],
            expected_kept_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
            ],
        ),
        on_cluster=ExpectedDiscoveryResultOnCluster(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                HostLabel("node2_live_label", "true", SectionName("labels")),
            ],
            expected_kept_labels={
                HostName("test-clusterhost"): [
                    HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                    HostLabel("node2_live_label", "true", SectionName("labels")),
                ],
                HostName("test-node1"): [
                    HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                ],
                HostName("test-node2"): [
                    HostLabel("node2_live_label", "true", SectionName("labels")),
                ],
            },
        ),
    ),
]


@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__discover_host_labels_and_services_on_realhost(
    realhost_scenario: RealHostScenario,
    discovery_test_case: DiscoveryTestCase,
) -> None:
    if discovery_test_case.only_host_labels:
        # check for consistency of the test case
        assert not discovery_test_case.expected_services
        return

    # unpack for readability
    host_name = realhost_scenario.hostname
    providers = realhost_scenario.providers

    plugins = DiscoveryPluginMapper(
        discovery_config=_EmptyDiscoveryConfig(),
        check_plugins=_TEST_CHECK_PLUGINS,
    )
    plugin_names = find_plugins(
        providers,
        [(plugin_name, plugin.sections) for plugin_name, plugin in plugins.items()],
    )

    discovered_services = discover_services(
        host_name,
        plugin_names,
        providers=providers,
        plugins=plugins,
        on_error=OnError.RAISE,
    )

    services = {s.id() for s in discovered_services}

    assert services == discovery_test_case.expected_services


@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__perform_host_label_discovery_on_realhost(
    realhost_scenario: RealHostScenario,
    discovery_test_case: DiscoveryTestCase,
) -> None:
    scenario = realhost_scenario

    host_label_result = QualifiedDiscovery[HostLabel](
        preexisting=(
            DiscoveredHostLabelsStore(
                scenario.hostname, cmk.utils.paths.discovered_host_labels_dir
            ).load()
            if discovery_test_case.load_labels
            else ()
        ),
        current=discover_host_labels(
            scenario.hostname,
            HostLabelPluginMapper(
                discovery_config=_EmptyDiscoveryConfig(),
                sections=_TEST_AGENT_SECTIONS,
            ),
            providers=scenario.providers,
            on_error=OnError.RAISE,
        ),
    )

    assert (
        host_label_result.vanished == discovery_test_case.on_realhost.expected_vanished_host_labels
    )
    assert host_label_result.old == discovery_test_case.on_realhost.expected_old_host_labels
    assert host_label_result.new == discovery_test_case.on_realhost.expected_new_host_labels

    assert host_label_result.present == discovery_test_case.on_realhost.expected_kept_labels


def test__discover_services_on_cluster(
    cluster_scenario: ClusterScenario,
) -> None:
    assert discovery_by_host(
        cluster_scenario.hosts_config.clusters[cluster_scenario.parent],
        cluster_scenario.providers,
        DiscoveryPluginMapper(
            discovery_config=_EmptyDiscoveryConfig(),
            check_plugins=_TEST_CHECK_PLUGINS,
        ),
        OnError.RAISE,
    ) == {
        "test-node1": [
            AutocheckEntry(
                check_plugin_name=_TEST_PLUGIN_NAME,
                item="item_a",
                parameters={},
                service_labels={},
            ),
        ],
        "test-node2": [
            AutocheckEntry(
                check_plugin_name=_TEST_PLUGIN_NAME,
                item="item_a",
                parameters={},
                service_labels={},
            ),
        ],
    }


@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__perform_host_label_discovery_on_cluster(
    cluster_scenario: ClusterScenario,
    discovery_test_case: DiscoveryTestCase,
) -> None:
    scenario = cluster_scenario
    nodes = scenario.hosts_config.clusters[scenario.parent]
    assert nodes

    host_label_result, kept_labels = analyse_cluster_labels(
        scenario.parent,
        nodes,
        discovered_host_labels={
            node: discover_host_labels(
                node,
                HostLabelPluginMapper(
                    discovery_config=_EmptyDiscoveryConfig(),
                    sections=_TEST_AGENT_SECTIONS,
                ),
                providers=scenario.providers,
                on_error=OnError.RAISE,
            )
            for node in nodes
        },
        existing_host_labels=(
            {
                node: DiscoveredHostLabelsStore(
                    node, cmk.utils.paths.discovered_host_labels_dir
                ).load()
                for node in nodes
            }
            if discovery_test_case.load_labels
            else {}
        ),
    )

    assert (
        host_label_result.vanished == discovery_test_case.on_cluster.expected_vanished_host_labels
    )
    assert host_label_result.old == discovery_test_case.on_cluster.expected_old_host_labels
    assert host_label_result.new == discovery_test_case.on_cluster.expected_new_host_labels
    assert kept_labels == discovery_test_case.on_cluster.expected_kept_labels


class _AutochecksConfigDummy:
    def ignore_plugin(self, hn: HostName, plugin: CheckPluginName) -> bool:
        return False

    def ignore_service(self, hn: HostName, entry: AutocheckEntry) -> bool:
        return False

    def effective_host(self, host_name: HostName, entry: AutocheckEntry) -> HostName:
        return host_name

    def service_description(self, host_name: HostName, entry: AutocheckEntry) -> str:
        return "desc"

    def service_labels(self, host_name: HostName, entry: AutocheckEntry) -> Mapping[str, str]:
        return {}


def test_get_node_services() -> None:
    host_name = HostName("horst")
    entries = QualifiedDiscovery[AutocheckEntry](
        preexisting=[
            AutocheckEntry(
                CheckPluginName(f"plugin_{discovery_status}"),
                item=None,
                parameters={},
                service_labels={},
            )
            for discovery_status in ("unchanged", "vanished")
        ],
        current=[
            AutocheckEntry(
                CheckPluginName(f"plugin_{discovery_status}"),
                item=None,
                parameters={},
                service_labels={},
            )
            for discovery_status in ("unchanged", "new")
        ],
    )
    assert make_table(host_name, entries, autochecks_config=_AutochecksConfigDummy()) == {
        ServiceID(CheckPluginName("plugin_vanished"), item=None): ServicesTableEntry(
            transition="vanished",
            autocheck=DiscoveredItem[AutocheckEntry](
                previous=AutocheckEntry(
                    CheckPluginName("plugin_vanished"),
                    item=None,
                    parameters={},
                    service_labels={},
                ),
                new=None,
            ),
            hosts=[host_name],
        ),
        ServiceID(CheckPluginName("plugin_unchanged"), item=None): ServicesTableEntry(
            transition="unchanged",
            autocheck=DiscoveredItem[AutocheckEntry](
                previous=AutocheckEntry(
                    CheckPluginName("plugin_unchanged"),
                    item=None,
                    parameters={},
                    service_labels={},
                ),
                new=AutocheckEntry(
                    CheckPluginName("plugin_unchanged"),
                    item=None,
                    parameters={},
                    service_labels={},
                ),
            ),
            hosts=[host_name],
        ),
        ServiceID(CheckPluginName("plugin_new"), item=None): ServicesTableEntry(
            transition="new",
            autocheck=DiscoveredItem[AutocheckEntry](
                new=AutocheckEntry(
                    CheckPluginName("plugin_new"),
                    item=None,
                    parameters={},
                    service_labels={},
                ),
                previous=None,
            ),
            hosts=[host_name],
        ),
    }


def test_make_discovery_diff_empty() -> None:
    assert _make_diff((), (), (), ()) == "Nothing was changed."


class _MockService(NamedTuple):
    check_plugin_name: CheckPluginName
    item: str | None


def test_make_discovery_diff() -> None:
    assert _make_diff(
        (HostLabel("foo", "bar"),),
        (HostLabel("gee", "boo"),),
        (DiscoveredItem(previous=_MockService(CheckPluginName("norris"), "chuck"), new=None),),  # type: ignore[arg-type]
        (DiscoveredItem(previous=_MockService(CheckPluginName("chan"), None), new=None),),  # type: ignore[arg-type]
    ) == (
        "Removed host label: 'foo:bar'.\n"
        "Added host label: 'gee:boo'.\n"
        "Removed service: Check plug-in 'norris' / item 'chuck'.\n"
        "Added service: Check plug-in 'chan'."
    )
