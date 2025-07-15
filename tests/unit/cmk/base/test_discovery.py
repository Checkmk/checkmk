#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
import socket
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import pytest
from pytest import MonkeyPatch

from tests.testlib.unit.base_configuration_scenario import Scenario

from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.rulesets import RuleSetName
from cmk.utils.sectionname import SectionName

from cmk.snmplib import SNMPRawData

from cmk.fetchers import Mode
from cmk.fetchers.filecache import FileCacheOptions

from cmk.checkengine.checkresults import ActiveCheckResult
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
from cmk.checkengine.discovery._active_check import _check_host_labels, _check_service_lists
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
from cmk.checkengine.discovery._filters import RediscoveryParameters, ServiceFilters
from cmk.checkengine.discovery._utils import DiscoveredItem
from cmk.checkengine.fetcher import HostKey, SourceType
from cmk.checkengine.parser import AgentRawDataSection, HostSections, NO_SELECTION
from cmk.checkengine.plugins import AgentBasedPlugins, AutocheckEntry, CheckPluginName, ServiceID
from cmk.checkengine.sectionparser import (
    ParsedSectionName,
    ParsedSectionsResolver,
    Provider,
    SectionPlugin,
    SectionsParser,
)

from cmk.base import config
from cmk.base.checkers import (
    CMKFetcher,
    CMKParser,
    DiscoveryPluginMapper,
    HostLabelPluginMapper,
    SectionPluginMapper,
)
from cmk.base.config import ConfigCache
from cmk.base.configlib.checkengine import DiscoveryConfig

from cmk.agent_based.v2 import AgentSection, SimpleSNMPSection
from cmk.plugins.collection.agent_based.df_section import agent_section_df
from cmk.plugins.collection.agent_based.kernel import agent_section_kernel
from cmk.plugins.collection.agent_based.labels import agent_section_labels
from cmk.plugins.collection.agent_based.uptime import agent_section_uptime
from cmk.plugins.liebert.agent_based.liebert_fans import snmp_section_liebert_fans


def _as_plugin(plugin: AgentSection | SimpleSNMPSection) -> SectionPlugin:
    return SectionPlugin(
        supersedes=set()
        if plugin.supersedes is None
        else {SectionName(n) for n in plugin.supersedes},
        parse_function=plugin.parse_function,
        parsed_section_name=ParsedSectionName(plugin.parsed_section_name or plugin.name),
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


def test__find_candidates(
    monkeypatch: MonkeyPatch,
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    # plugins have been loaded by the fixture. Better: load the ones we need for this test
    Scenario().apply(monkeypatch)
    providers = {
        # we just care about the keys here, content set to arbitrary values that can be parsed.
        # section names are chosen arbitrarily.
        HostKey(HostName("test_node"), SourceType.HOST): (
            ParsedSectionsResolver(
                SectionsParser(
                    host_sections=HostSections[AgentRawDataSection](
                        {
                            SectionName("kernel"): [],  # host only
                            SectionName("uptime"): [["123"]],  # host & mgmt
                        }
                    ),
                    host_name=HostName("test_node"),
                    error_handling=lambda *args, **kw: "error",
                ),
                section_plugins={
                    SectionName("kernel"): _as_plugin(agent_section_kernel),
                    SectionName("uptime"): _as_plugin(agent_section_uptime),
                },
            )
        ),
        HostKey(HostName("test_node"), SourceType.MANAGEMENT): (
            ParsedSectionsResolver(
                SectionsParser(
                    host_sections=HostSections[SNMPRawData](
                        {
                            # host & mgmt:
                            SectionName("uptime"): [["123"]],
                            # mgmt only:
                            SectionName("liebert_fans"): [[["Fan", "67", "umin"]]],
                            # is already mgmt_ prefixed:
                            SectionName("mgmt_snmp_info"): [[["a", "b", "c", "d"]]],
                        }
                    ),
                    host_name=HostName("test_node"),
                    error_handling=lambda *args, **kw: "error",
                ),
                section_plugins={
                    SectionName("uptime"): _as_plugin(agent_section_uptime),
                    SectionName("liebert_fans"): _as_plugin(snmp_section_liebert_fans),
                    SectionName("mgmt_snmp_info"): SectionPlugin(
                        supersedes=set(),
                        parsed_section_name=ParsedSectionName("mgmt_snmp_info"),
                        parse_function=lambda x: x,
                    ),
                },
            )
        ),
    }

    assert find_plugins(
        providers,
        [(p.name, p.sections) for p in agent_based_plugins.check_plugins.values()],
    ) == {
        CheckPluginName("docker_container_status_uptime"),
        CheckPluginName("kernel"),
        CheckPluginName("kernel_performance"),
        CheckPluginName("kernel_util"),
        CheckPluginName("mgmt_docker_container_status_uptime"),
        CheckPluginName("mgmt_liebert_fans"),
        CheckPluginName("mgmt_uptime"),
        CheckPluginName("uptime"),
    }


_expected_services: dict = {
    (CheckPluginName("apache_status"), "127.0.0.1:5000"): {},
    (CheckPluginName("apache_status"), "127.0.0.1:5004"): {},
    (CheckPluginName("apache_status"), "127.0.0.1:5007"): {},
    (CheckPluginName("apache_status"), "127.0.0.1:5008"): {},
    (CheckPluginName("apache_status"), "127.0.0.1:5009"): {},
    (CheckPluginName("apache_status"), "::1:80"): {},
    (CheckPluginName("checkmk_agent"), None): {},
    (CheckPluginName("cpu_loads"), None): {},
    (CheckPluginName("cpu_threads"), None): {},
    (CheckPluginName("df"), "/"): {},
    (CheckPluginName("df"), "/boot"): {},
    (CheckPluginName("df"), "/boot/efi"): {},
    (CheckPluginName("diskstat"), "SUMMARY"): {},
    (CheckPluginName("kernel_performance"), None): {},
    (CheckPluginName("kernel_util"), None): {},
    (CheckPluginName("livestatus_status"), "heute"): {},
    (CheckPluginName("livestatus_status"), "test1"): {},
    (CheckPluginName("livestatus_status"), "test2"): {},
    (CheckPluginName("livestatus_status"), "test3"): {},
    (CheckPluginName("livestatus_status"), "test_crawl"): {},
    (CheckPluginName("lnx_if"), "2"): {},
    (CheckPluginName("lnx_if"), "3"): {},
    (CheckPluginName("lnx_thermal"), "Zone 0"): {},
    (CheckPluginName("lnx_thermal"), "Zone 1"): {},
    (CheckPluginName("logwatch"), "/var/log/auth.log"): {},
    (CheckPluginName("logwatch"), "/var/log/kern.log"): {},
    (CheckPluginName("logwatch"), "/var/log/syslog"): {},
    (CheckPluginName("local"), "SäMB_Share_flr01"): {},
    (CheckPluginName("mem_linux"), None): {},
    (CheckPluginName("mkeventd_status"), "heute"): {},
    (CheckPluginName("mkeventd_status"), "test1"): {},
    (CheckPluginName("mkeventd_status"), "test2"): {},
    (CheckPluginName("mkeventd_status"), "test3"): {},
    (CheckPluginName("mkeventd_status"), "test_crawl"): {},
    (CheckPluginName("mknotifyd"), "heute"): {},
    (CheckPluginName("mknotifyd"), "heute_slave_1"): {},
    (CheckPluginName("mknotifyd"), "test1"): {},
    (CheckPluginName("mknotifyd"), "test2"): {},
    (CheckPluginName("mknotifyd"), "test3"): {},
    (CheckPluginName("mknotifyd"), "test_crawl"): {},
    (CheckPluginName("mounts"), "/"): {},
    (CheckPluginName("mounts"), "/boot"): {},
    (CheckPluginName("mounts"), "/boot/efi"): {},
    (CheckPluginName("ntp_time"), None): {},
    (CheckPluginName("omd_apache"), "aq"): {},
    (CheckPluginName("omd_apache"), "heute"): {},
    (CheckPluginName("omd_apache"), "heute_slave_1"): {},
    (CheckPluginName("omd_apache"), "onelogin"): {},
    (CheckPluginName("omd_apache"), "stable"): {},
    (CheckPluginName("omd_apache"), "stable_slave_1"): {},
    (CheckPluginName("omd_apache"), "test1"): {},
    (CheckPluginName("omd_apache"), "test2"): {},
    (CheckPluginName("omd_apache"), "test3"): {},
    (CheckPluginName("omd_apache"), "test_crawl"): {},
    (CheckPluginName("omd_status"), "heute"): {},
    (CheckPluginName("omd_status"), "test1"): {},
    (CheckPluginName("omd_status"), "test2"): {},
    (CheckPluginName("omd_status"), "test3"): {},
    (CheckPluginName("omd_status"), "test_crawl"): {},
    (CheckPluginName("postfix_mailq"), "default"): {},
    (CheckPluginName("postfix_mailq_status"), "postfix"): {},
    (CheckPluginName("tcp_conn_stats"), None): {},
    (CheckPluginName("uptime"), None): {},
}

_expected_host_labels = [
    HostLabel("cmk/os_family", "linux", SectionName("check_mk")),
    HostLabel("cmk/os_type", "linux", SectionName("check_mk")),
    HostLabel("cmk/os_platform", "ubuntu", SectionName("check_mk")),
    HostLabel("cmk/os_name", "Ubuntu", SectionName("check_mk")),
    HostLabel("cmk/os_version", "22.04", SectionName("check_mk")),
]


class _EmptyDiscoveryConfig(ABCDiscoveryConfig):
    def __call__(
        self, host_name: object, rule_set_name: object, rule_set_type: str
    ) -> Mapping[str, object] | Sequence[Mapping[str, object]]:
        return [] if rule_set_type == "all" else {}


@pytest.mark.usefixtures("patch_omd_site")
def test_commandline_discovery(
    monkeypatch: MonkeyPatch,
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    testhost = HostName("test-host")
    ts = Scenario()
    ts.add_host(testhost, ipaddress=HostAddress("127.0.0.1"))
    ts.fake_standard_linux_agent_output(testhost)
    config_cache = ts.apply(monkeypatch)

    # damn you logwatch!!
    config._globally_cache_config_cache(config_cache)

    file_cache_options = FileCacheOptions()
    parser = CMKParser(
        config_cache.parser_factory(),
        selected_sections=NO_SELECTION,
        keep_outdated=file_cache_options.keep_outdated,
        logger=logging.getLogger("tests"),
    )
    fetcher = CMKFetcher(
        config_cache,
        config_cache.fetcher_factory(
            config_cache.make_service_configurer(
                {}, config_cache.make_passive_service_name_config()
            ),
            ip_lookup=lambda *a: HostAddress(""),
        ),
        agent_based_plugins,
        default_address_family=lambda *a: socket.AddressFamily.AF_INET,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=False,
        get_ip_stack_config=lambda *a: IPStackConfig.IPv4,
        ip_address_of=lambda *a: HostAddress(""),
        ip_address_of_mandatory=lambda *a: HostAddress(""),
        ip_address_of_mgmt=lambda *a: HostAddress(""),
        mode=Mode.DISCOVERY,
        on_error=OnError.RAISE,
        selected_sections=NO_SELECTION,
        simulation_mode=True,
        snmp_backend_override=None,
        password_store_file=Path("/pw/store"),
    )

    commandline_discovery(
        host_name=testhost,
        clear_ruleset_matcher_caches=config_cache.ruleset_matcher.clear_caches,
        parser=parser,
        fetcher=fetcher,
        section_plugins=SectionPluginMapper(
            {**agent_based_plugins.agent_sections, **agent_based_plugins.snmp_sections}
        ),
        section_error_handling=lambda *args, **kw: "error",
        host_label_plugins=HostLabelPluginMapper(
            discovery_config=_EmptyDiscoveryConfig(),
            sections={**agent_based_plugins.agent_sections, **agent_based_plugins.snmp_sections},
        ),
        plugins=DiscoveryPluginMapper(
            discovery_config=_EmptyDiscoveryConfig(),
            check_plugins=agent_based_plugins.check_plugins,
        ),
        run_plugin_names=EVERYTHING,
        ignore_plugin=lambda *args, **kw: False,
        arg_only_new=False,
        on_error=OnError.RAISE,
    )

    entries = AutochecksStore(testhost).read()
    found = {e.id(): e.service_labels for e in entries}
    assert found == _expected_services

    store = DiscoveredHostLabelsStore(testhost)
    assert store.load() == _expected_host_labels


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
    config_cache = ts.apply(monkeypatch)

    DiscoveredHostLabelsStore(hostname).save(
        [
            HostLabel("existing_label", "bar", SectionName("foo")),
            HostLabel("another_label", "true", SectionName("labels")),
        ]
    )

    providers = {
        HostKey(hostname=hostname, source_type=SourceType.HOST): (
            ParsedSectionsResolver(
                SectionsParser(
                    host_sections=HostSections[AgentRawDataSection](
                        sections={
                            SectionName("labels"): [
                                [
                                    '{"cmk/check_mk_server":"yes"}',
                                ],
                            ],
                            SectionName("df"): [
                                [
                                    "/dev/sda1",
                                    "vfat",
                                    "523248",
                                    "3668",
                                    "519580",
                                    "1%",
                                    "/boot/test-efi",
                                ],
                                [
                                    "tmpfs",
                                    "tmpfs",
                                    "8152916",
                                    "244",
                                    "8152672",
                                    "1%",
                                    "/opt/omd/sites/test-heute/tmp",
                                ],
                            ],
                        }
                    ),
                    host_name=hostname,
                    error_handling=lambda *args, **kw: "error",
                ),
                section_plugins={
                    SectionName("labels"): _as_plugin(agent_section_labels),
                    SectionName("df"): _as_plugin(agent_section_df),
                },
            )
        )
    }

    return RealHostScenario(hostname, config_cache, providers)


class ClusterScenario(NamedTuple):
    parent: HostName
    config_cache: ConfigCache
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
                    "service_description": [{"$regex": "fs_"}],
                    "host_name": [node1_hostname],
                },
                "value": True,
            }
        ],
    )
    config_cache = ts.apply(monkeypatch)

    DiscoveredHostLabelsStore(node1_hostname).save(
        [HostLabel("node1_existing_label", "true", SectionName("node1_plugin"))]
    )

    providers = {
        HostKey(hostname=node1_hostname, source_type=SourceType.HOST): (
            ParsedSectionsResolver(
                SectionsParser(
                    host_sections=HostSections[AgentRawDataSection](
                        sections={
                            SectionName("labels"): [
                                [
                                    '{"cmk/check_mk_server":"yes"}',
                                ]
                            ],
                            SectionName("df"): [
                                [
                                    "/dev/sda1",
                                    "vfat",
                                    "523248",
                                    "3668",
                                    "519580",
                                    "1%",
                                    "/boot/test-efi",
                                ],
                                [
                                    "tmpfs",
                                    "tmpfs",
                                    "8152916",
                                    "244",
                                    "8152672",
                                    "1%",
                                    "/opt/omd/sites/test-heute/tmp",
                                ],
                            ],
                        }
                    ),
                    host_name=node1_hostname,
                    error_handling=lambda *args, **kw: "error",
                ),
                section_plugins={
                    SectionName("labels"): _as_plugin(agent_section_labels),
                    SectionName("df"): _as_plugin(agent_section_df),
                },
            )
        ),
        HostKey(hostname=node2_hostname, source_type=SourceType.HOST): (
            ParsedSectionsResolver(
                SectionsParser(
                    host_sections=HostSections[AgentRawDataSection](
                        sections={
                            SectionName("labels"): [
                                [
                                    '{"node2_live_label":"true"}',
                                ],
                            ],
                            SectionName("df"): [
                                [
                                    "/dev/sda1",
                                    "vfat",
                                    "523248",
                                    "3668",
                                    "519580",
                                    "1%",
                                    "/boot/test-efi",
                                ],
                                [
                                    "tmpfs",
                                    "tmpfs",
                                    "8152916",
                                    "244",
                                    "8152672",
                                    "1%",
                                    "/opt/omd/sites/test-heute2/tmp",
                                ],
                            ],
                        }
                    ),
                    host_name=node2_hostname,
                    error_handling=lambda *args, **kw: "error",
                ),
                section_plugins={
                    SectionName("labels"): _as_plugin(agent_section_labels),
                    SectionName("df"): _as_plugin(agent_section_df),
                },
            )
        ),
    }

    return ClusterScenario(
        hostname,
        config_cache,
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
        ((), {ServiceID(CheckPluginName("df"), "/boot/test-efi")}),
        (
            (HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),),
            {
                ServiceID(CheckPluginName("df"), "/boot/test-efi"),
                ServiceID(CheckPluginName("df"), "/opt/omd/sites/test-heute/tmp"),
            },
        ),
    ],
)
def test__discovery_considers_host_labels(
    host_labels: tuple[HostLabel],
    expected_services: set[ServiceID],
    realhost_scenario: RealHostScenario,
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    # this takes the detour via ruleset matcher :-(
    DiscoveredHostLabelsStore(realhost_scenario.hostname).save(host_labels)

    # unpack for readability
    host_name = realhost_scenario.hostname
    config_cache = realhost_scenario.config_cache
    providers = realhost_scenario.providers

    # arrange
    plugins = DiscoveryPluginMapper(
        discovery_config=DiscoveryConfig(
            config_cache.ruleset_matcher,
            config_cache.label_manager.labels_of_host,
            rules={
                RuleSetName("mssql_transactionlogs_discovery"): [],
                RuleSetName("inventory_df_rules"): [
                    {
                        "id": "nobody-cares-about-the-id-in-this-test",
                        "value": {
                            "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
                            "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
                        },
                        "condition": {
                            "host_label_groups": [("and", [("and", "cmk/check_mk_server:yes")])]
                        },
                    }
                ],
            },
        ),
        check_plugins=agent_based_plugins.check_plugins,
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
            (CheckPluginName("df"), "/boot/test-efi"),
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
            (CheckPluginName("df"), "/boot/test-efi"),
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
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    if discovery_test_case.only_host_labels:
        # check for consistency of the test case
        assert not discovery_test_case.expected_services
        return

    # unpack for readability
    host_name = realhost_scenario.hostname
    providers = realhost_scenario.providers

    # arrange
    plugins = DiscoveryPluginMapper(
        discovery_config=_EmptyDiscoveryConfig(),
        check_plugins=agent_based_plugins.check_plugins,
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


@pytest.mark.usefixtures("agent_based_plugins")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__perform_host_label_discovery_on_realhost(
    realhost_scenario: RealHostScenario,
    discovery_test_case: DiscoveryTestCase,
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    scenario = realhost_scenario

    host_label_result = QualifiedDiscovery[HostLabel](
        preexisting=(
            DiscoveredHostLabelsStore(scenario.hostname).load()
            if discovery_test_case.load_labels
            else ()
        ),
        current=discover_host_labels(
            scenario.hostname,
            HostLabelPluginMapper(
                discovery_config=_EmptyDiscoveryConfig(),
                sections={
                    **agent_based_plugins.agent_sections,
                    **agent_based_plugins.snmp_sections,
                },
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
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    assert discovery_by_host(
        cluster_scenario.config_cache.nodes(cluster_scenario.parent),
        cluster_scenario.providers,
        DiscoveryPluginMapper(
            discovery_config=_EmptyDiscoveryConfig(),
            check_plugins=agent_based_plugins.check_plugins,
        ),
        OnError.RAISE,
    ) == {
        "test-node1": [
            AutocheckEntry(
                check_plugin_name=CheckPluginName("df"),
                item="/boot/test-efi",
                parameters={
                    "mountpoint_for_block_devices": "volume_name",
                    "item_appearance": "mountpoint",
                },
                service_labels={},
            ),
        ],
        "test-node2": [
            AutocheckEntry(
                check_plugin_name=CheckPluginName("df"),
                item="/boot/test-efi",
                parameters={
                    "mountpoint_for_block_devices": "volume_name",
                    "item_appearance": "mountpoint",
                },
                service_labels={},
            ),
        ],
    }


@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__perform_host_label_discovery_on_cluster(
    cluster_scenario: ClusterScenario,
    discovery_test_case: DiscoveryTestCase,
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    scenario = cluster_scenario
    nodes = scenario.config_cache.nodes(scenario.parent)
    assert nodes

    host_label_result, kept_labels = analyse_cluster_labels(
        scenario.parent,
        nodes,
        discovered_host_labels={
            node: discover_host_labels(
                node,
                HostLabelPluginMapper(
                    discovery_config=_EmptyDiscoveryConfig(),
                    sections={
                        **agent_based_plugins.agent_sections,
                        **agent_based_plugins.snmp_sections,
                    },
                ),
                providers=scenario.providers,
                on_error=OnError.RAISE,
            )
            for node in nodes
        },
        existing_host_labels=(
            {node: DiscoveredHostLabelsStore(node).load() for node in nodes}
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
