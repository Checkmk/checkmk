#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import logging
from collections.abc import Mapping, Sequence
from typing import Any, Iterable, NamedTuple

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests.testlib.base import Scenario

from cmk.utils.exceptions import OnError
from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.type_defs import (
    CheckPluginName,
    DiscoveryResult,
    EVERYTHING,
    HostName,
    RuleSetName,
    SectionName,
    ServiceID,
)

from cmk.snmplib.type_defs import SNMPRawDataSection

from cmk.fetchers import Mode
from cmk.fetchers.filecache import FileCacheOptions

from cmk.checkers import HostKey, SourceType
from cmk.checkers.checkresults import ActiveCheckResult
from cmk.checkers.discovery import AutocheckEntry, AutocheckServiceWithNodes, AutochecksStore
from cmk.checkers.host_sections import HostSections
from cmk.checkers.type_defs import AgentRawDataSection, NO_SELECTION

import cmk.base.agent_based.discovery as discovery
import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
from cmk.base.agent_based.confcheckers import (
    CheckPluginMapper,
    ConfiguredFetcher,
    ConfiguredParser,
    HostLabelPluginMapper,
    SectionPluginMapper,
)
from cmk.base.agent_based.data_provider import (
    ParsedSectionName,
    ParsedSectionsResolver,
    Provider,
    SectionsParser,
)
from cmk.base.agent_based.discovery import _discovered_services
from cmk.base.agent_based.discovery._discovery import _check_host_labels, _check_service_lists
from cmk.base.agent_based.discovery._host_labels import (
    analyse_cluster_labels,
    analyse_host_labels,
    discover_host_labels,
    do_load_labels,
)
from cmk.base.agent_based.discovery.autodiscovery import (
    _get_cluster_services,
    _get_node_services,
    _get_post_discovery_autocheck_services,
    _group_by_transition,
    _make_diff,
    _ServiceFilters,
    ServicesByTransition,
    ServicesTable,
)
from cmk.base.agent_based.discovery.utils import DiscoveryMode, QualifiedDiscovery
from cmk.base.config import ConfigCache


@pytest.fixture
def service_table() -> ServicesTable:
    return {
        ServiceID(CheckPluginName("check_plugin_name"), "New Item 1"): (
            "new",
            AutocheckEntry(
                CheckPluginName("check_plugin_name"),
                "New Item 1",
                "Test Description New Item 1",
                {},
            ),
            [],
        ),
        ServiceID(CheckPluginName("check_plugin_name"), "New Item 2"): (
            "new",
            AutocheckEntry(
                CheckPluginName("check_plugin_name"),
                "New Item 2",
                "Test Description New Item 2",
                {},
            ),
            [],
        ),
        ServiceID(CheckPluginName("check_plugin_name"), "Vanished Item 1"): (
            "vanished",
            AutocheckEntry(
                CheckPluginName("check_plugin_name"),
                "Vanished Item 1",
                "Test Description Vanished Item 1",
                {},
            ),
            [],
        ),
        ServiceID(CheckPluginName("check_plugin_name"), "Vanished Item 2"): (
            "vanished",
            AutocheckEntry(
                CheckPluginName("check_plugin_name"),
                "Vanished Item 2",
                "Test Description Vanished Item 2",
                {},
            ),
            [],
        ),
    }


@pytest.fixture
def grouped_services() -> ServicesByTransition:
    return {
        "new": [
            AutocheckServiceWithNodes(
                AutocheckEntry(
                    CheckPluginName("check_plugin_name"),
                    "New Item 1",
                    "Test Description New Item 1",
                    {},
                ),
                [],
            ),
            AutocheckServiceWithNodes(
                AutocheckEntry(
                    CheckPluginName("check_plugin_name"),
                    "New Item 2",
                    "Test Description New Item 2",
                    {},
                ),
                [],
            ),
        ],
        "vanished": [
            AutocheckServiceWithNodes(
                AutocheckEntry(
                    CheckPluginName("check_plugin_name"),
                    "Vanished Item 1",
                    "Test Description Vanished Item 1",
                    {},
                ),
                [],
            ),
            AutocheckServiceWithNodes(
                AutocheckEntry(
                    CheckPluginName("check_plugin_name"),
                    "Vanished Item 2",
                    "Test Description Vanished Item 2",
                    {},
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
            DiscoveryMode.NEW,
            {},
            ["New Item 1", "New Item 2", "Vanished Item 1", "Vanished Item 2"],
            (2, 2, 0),
        ),
        (DiscoveryMode.FIXALL, {}, ["New Item 1", "New Item 2"], (2, 0, 2)),
        (
            DiscoveryMode.REFRESH,
            {},
            ["New Item 1", "New Item 2", "Vanished Item 1", "Vanished Item 2"],
            (2, 2, 0),
        ),
        (DiscoveryMode.REMOVE, {}, [], (0, 0, 2)),
        # New services
        # Whitelist
        (
            DiscoveryMode.NEW,
            {"service_whitelist": ["^Test Description New Item 1"]},
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            DiscoveryMode.FIXALL,
            {"service_whitelist": ["^Test Description New Item 1"]},
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            DiscoveryMode.REFRESH,
            {"service_whitelist": ["^Test Description New Item 1"]},
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            DiscoveryMode.REMOVE,
            {"service_whitelist": ["^Test Description New Item 1"]},
            ["Vanished Item 1", "Vanished Item 2"],
            (0, 2, 0),
        ),
        # Blacklist
        (
            DiscoveryMode.NEW,
            {"service_blacklist": ["^Test Description New Item 1"]},
            ["New Item 2", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            DiscoveryMode.FIXALL,
            {"service_blacklist": ["^Test Description New Item 1"]},
            ["New Item 2"],
            (1, 0, 2),
        ),
        (
            DiscoveryMode.REFRESH,
            {"service_blacklist": ["^Test Description New Item 1"]},
            ["New Item 2", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            DiscoveryMode.REMOVE,
            {"service_blacklist": ["^Test Description New Item 1"]},
            [],
            (0, 0, 2),
        ),
        # White-/blacklist
        (
            DiscoveryMode.NEW,
            {
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            DiscoveryMode.FIXALL,
            {
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            DiscoveryMode.REFRESH,
            {
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
            ["New Item 1", "Vanished Item 1", "Vanished Item 2"],
            (1, 2, 0),
        ),
        (
            DiscoveryMode.REMOVE,
            {
                "service_whitelist": ["^Test Description New Item 1"],
                "service_blacklist": ["^Test Description New Item 2"],
            },
            ["Vanished Item 1", "Vanished Item 2"],
            (0, 2, 0),
        ),
        # Vanished services
        # Whitelist
        (
            DiscoveryMode.NEW,
            {"service_whitelist": ["^Test Description Vanished Item 1"]},
            ["Vanished Item 1", "Vanished Item 2"],
            (0, 2, 0),
        ),
        (
            DiscoveryMode.FIXALL,
            {"service_whitelist": ["^Test Description Vanished Item 1"]},
            ["Vanished Item 2"],
            (0, 1, 1),
        ),
        (
            DiscoveryMode.REFRESH,
            {"service_whitelist": ["^Test Description Vanished Item 1"]},
            ["Vanished Item 1", "Vanished Item 2"],
            (0, 2, 0),
        ),
        (
            DiscoveryMode.REMOVE,
            {"service_whitelist": ["^Test Description Vanished Item 1"]},
            ["Vanished Item 2"],
            (0, 1, 1),
        ),
        # Blacklist
        (
            DiscoveryMode.NEW,
            {"service_blacklist": ["^Test Description Vanished Item 1"]},
            ["New Item 1", "New Item 2", "Vanished Item 1", "Vanished Item 2"],
            (2, 2, 0),
        ),
        (
            DiscoveryMode.FIXALL,
            {"service_blacklist": ["^Test Description Vanished Item 1"]},
            ["New Item 1", "New Item 2", "Vanished Item 1"],
            (2, 1, 1),
        ),
        (
            DiscoveryMode.REFRESH,
            {"service_blacklist": ["^Test Description Vanished Item 1"]},
            ["New Item 1", "New Item 2", "Vanished Item 1", "Vanished Item 2"],
            (2, 2, 0),
        ),
        (
            DiscoveryMode.REMOVE,
            {"service_blacklist": ["^Test Description Vanished Item 1"]},
            ["Vanished Item 1"],
            (0, 1, 1),
        ),
        # White-/blacklist
        (
            DiscoveryMode.NEW,
            {
                "service_whitelist": ["^Test Description Vanished Item 1"],
                "service_blacklist": ["^Test Description Vanished Item 2"],
            },
            ["Vanished Item 1", "Vanished Item 2"],
            (0, 2, 0),
        ),
        (
            DiscoveryMode.FIXALL,
            {
                "service_whitelist": ["^Test Description Vanished Item 1"],
                "service_blacklist": ["^Test Description Vanished Item 2"],
            },
            ["Vanished Item 2"],
            (0, 1, 1),
        ),
        (
            DiscoveryMode.REFRESH,
            {
                "service_whitelist": ["^Test Description Vanished Item 1"],
                "service_blacklist": ["^Test Description Vanished Item 2"],
            },
            ["Vanished Item 1", "Vanished Item 2"],
            (0, 2, 0),
        ),
        (
            DiscoveryMode.REMOVE,
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
    mode: DiscoveryMode,
    parameters_rediscovery: dict[str, list[str]],
    result_new_item_names: list[str],
    result_counts: tuple[int, int, int],
) -> None:
    result = DiscoveryResult()

    service_filters = _ServiceFilters.from_settings(parameters_rediscovery)

    new_item_names = [
        entry.service.item or ""
        for entry in _get_post_discovery_autocheck_services(
            HostName("hostname"),
            grouped_services,
            service_filters,
            result,
            find_service_description=lambda *args: f"Test Description {args[-1]}",
            mode=mode,
            keep_clustered_vanished_services=True,
        ).values()
    ]

    count_new, count_kept, count_removed = result_counts

    assert sorted(new_item_names) == sorted(result_new_item_names)
    assert result.self_new == count_new
    assert result.self_kept == count_kept
    assert result.self_removed == count_removed


def _get_params(rediscovery: dict[str, Any]) -> config.DiscoveryCheckParameters:
    return config.DiscoveryCheckParameters(
        commandline_only=False,
        check_interval=60,
        severity_new_services=1,
        severity_vanished_services=0,
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
                    "mode": DiscoveryMode.NEW,
                    "service_whitelist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REMOVE,
                    "service_whitelist": ["^Test Description New Item 1"],
                }
            ),
            False,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.FIXALL,
                    "service_whitelist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REFRESH,
                    "service_whitelist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        # Blacklist
        (
            _get_params(
                {
                    "mode": DiscoveryMode.NEW,
                    "service_blacklist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REMOVE,
                    "service_blacklist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.FIXALL,
                    "service_blacklist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REFRESH,
                    "service_blacklist": ["^Test Description New Item 1"],
                }
            ),
            True,
        ),
        # White-/blacklist
        (
            _get_params(
                {
                    "mode": DiscoveryMode.NEW,
                    "service_whitelist": ["^Test Description New Item 1"],
                    "service_blacklist": ["^Test Description New Item 2"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REMOVE,
                    "service_whitelist": ["^Test Description New Item 1"],
                    "service_blacklist": ["^Test Description New Item 2"],
                }
            ),
            False,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.FIXALL,
                    "service_whitelist": ["^Test Description New Item 1"],
                    "service_blacklist": ["^Test Description New Item 2"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REFRESH,
                    "service_whitelist": ["^Test Description New Item 1"],
                    "service_blacklist": ["^Test Description New Item 2"],
                }
            ),
            True,
        ),
        # Vanished services
        # Whitelist
        (
            _get_params(
                {
                    "mode": DiscoveryMode.NEW,
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                }
            ),
            False,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REMOVE,
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.FIXALL,
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REFRESH,
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        # Blacklist
        (
            _get_params(
                {
                    "mode": DiscoveryMode.NEW,
                    "service_blacklist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REMOVE,
                    "service_blacklist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.FIXALL,
                    "service_blacklist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REFRESH,
                    "service_blacklist": ["^Test Description Vanished Item 1"],
                }
            ),
            True,
        ),
        # White-/blacklist
        (
            _get_params(
                {
                    "mode": DiscoveryMode.NEW,
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                    "service_blacklist": ["^Test Description Vanished Item 2"],
                }
            ),
            False,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REMOVE,
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                    "service_blacklist": ["^Test Description Vanished Item 2"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.FIXALL,
                    "service_whitelist": ["^Test Description Vanished Item 1"],
                    "service_blacklist": ["^Test Description Vanished Item 2"],
                }
            ),
            True,
        ),
        (
            _get_params(
                {
                    "mode": DiscoveryMode.REFRESH,
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
    parameters: config.DiscoveryCheckParameters,
    result_need_rediscovery: bool,
) -> None:
    rediscovery_parameters = parameters.rediscovery.copy()
    discovery_mode = rediscovery_parameters.pop("mode", DiscoveryMode.FALLBACK)
    assert isinstance(discovery_mode, DiscoveryMode)  # for mypy
    results, need_rediscovery = _check_service_lists(
        host_name=HostName("hostname"),
        services_by_transition=grouped_services,
        params=parameters,
        service_filters=_ServiceFilters.from_settings(rediscovery_parameters),
        find_service_description=lambda *args: f"Test Description {args[-1]}",
        discovery_mode=discovery_mode,
    )

    assert results == [
        ActiveCheckResult(
            0,
            "",
            [
                "Unmonitored service: check_plugin_name: Test Description New Item 1",
            ],
        ),
        ActiveCheckResult(
            0,
            "",
            [
                "Unmonitored service: check_plugin_name: Test Description New Item 2",
            ],
        ),
        ActiveCheckResult(1, "Unmonitored services: 2 (check_plugin_name: 2)"),
        ActiveCheckResult(
            0,
            "",
            [
                "Vanished service: check_plugin_name: Test Description Vanished Item 1",
            ],
        ),
        ActiveCheckResult(
            0,
            "",
            [
                "Vanished service: check_plugin_name: Test Description Vanished Item 2",
            ],
        ),
        ActiveCheckResult(0, "Vanished services: 2 (check_plugin_name: 2)"),
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
            key=lambda l: l.name,
        ),
        1,
        DiscoveryMode.FIXALL,
    ) == ([ActiveCheckResult(0, "Host labels: all up to date")], False)


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
            key=lambda l: l.name,
        ),
        1,
        DiscoveryMode.FIXALL,
    ) == (
        [
            ActiveCheckResult(
                1, "New host labels: 1 (labels: 1)", ["New host label: labels: yetanotherone:isnew"]
            ),
            ActiveCheckResult(
                0,
                "Vanished host labels: 1 (my_section: 1)",
                ["Vanished host label: my_section: anotherone:vanishes"],
            ),
        ],
        True,
    )


@pytest.mark.usefixtures("fix_register")
def test__find_candidates() -> None:
    # This test doesn't test much:
    #  1. It concentrates on implementation details and private functions.
    #  2. Because it tests private functions, it also copy-pastes a lot of
    #     production code!
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
                ),
                section_plugins={
                    section_name: agent_based_register.get_section_plugin(section_name)
                    for section_name in (SectionName("kernel"), SectionName("uptime"))
                },
            )
        ),
        HostKey(HostName("test_node"), SourceType.MANAGEMENT): (
            ParsedSectionsResolver(
                SectionsParser(
                    host_sections=HostSections[SNMPRawDataSection](
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
                ),
                section_plugins={
                    section_name: agent_based_register.get_section_plugin(section_name)
                    for section_name in (
                        SectionName("uptime"),
                        SectionName("liebert_fans"),
                        SectionName("mgmt_snmp_info"),
                    )
                },
            )
        ),
    }

    preliminary_candidates = list(agent_based_register.iter_all_check_plugins())
    parsed_sections_of_interest = {
        parsed_section_name
        for plugin in preliminary_candidates
        for parsed_section_name in plugin.sections
    }

    def __iter(
        section_names: Iterable[ParsedSectionName], providers: Mapping[HostKey, Provider]
    ) -> Iterable[tuple[HostKey, ParsedSectionName]]:
        for host_key, provider in providers.items():
            # filter section names for sections that cannot be resolved
            for section_name in (
                section_name
                for section_name in section_names
                if provider.resolve(section_name) is not None
            ):
                yield host_key, section_name

    resolved = tuple(__iter(parsed_sections_of_interest, providers))

    assert discovery._discovered_services._find_host_candidates(
        ((p.name, p.sections) for p in preliminary_candidates),
        frozenset(
            section_name
            for host_key, section_name in resolved
            if host_key.source_type is SourceType.HOST
        ),
    ) == {
        CheckPluginName("docker_container_status_uptime"),
        CheckPluginName("kernel"),
        CheckPluginName("kernel_performance"),
        CheckPluginName("kernel_util"),
        CheckPluginName("uptime"),
    }

    assert discovery._discovered_services._find_mgmt_candidates(
        ((p.name, p.sections) for p in preliminary_candidates),
        frozenset(
            section_name
            for host_key, section_name in resolved
            if host_key.source_type is SourceType.MANAGEMENT
        ),
    ) == {
        CheckPluginName("mgmt_docker_container_status_uptime"),
        CheckPluginName("mgmt_liebert_fans"),
        CheckPluginName("mgmt_uptime"),
    }

    assert discovery._discovered_services._find_candidates(
        providers, [(name, p.sections) for name, p in CheckPluginMapper().items()]
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
    (CheckPluginName("postfix_mailq"), ""): {},
    (CheckPluginName("postfix_mailq_status"), ""): {},
    (CheckPluginName("tcp_conn_stats"), None): {},
    (CheckPluginName("uptime"), None): {},
}

_expected_host_labels = {
    "cmk/os_family": {
        "plugin_name": "check_mk",
        "value": "linux",
    },
}


@pytest.mark.usefixtures("fix_register")
def test_commandline_discovery(monkeypatch: MonkeyPatch) -> None:
    testhost = HostName("test-host")
    ts = Scenario()
    ts.add_host(testhost, ipaddress="127.0.0.1")
    ts.fake_standard_linux_agent_output(testhost)
    config_cache = ts.apply(monkeypatch)
    file_cache_options = FileCacheOptions()
    parser = ConfiguredParser(
        config_cache,
        selected_sections=NO_SELECTION,
        keep_outdated=file_cache_options.keep_outdated,
        logger=logging.getLogger("tests"),
    )
    fetcher = ConfiguredFetcher(
        config_cache,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=False,
        mode=Mode.DISCOVERY,
        on_error=OnError.RAISE,
        selected_sections=NO_SELECTION,
        simulation_mode=True,
    )
    discovery.commandline_discovery(
        arg_hostnames={testhost},
        config_cache=config_cache,
        parser=parser,
        fetcher=fetcher,
        section_plugins=SectionPluginMapper(),
        host_label_plugins=HostLabelPluginMapper(),
        check_plugins=CheckPluginMapper(),
        run_plugin_names=EVERYTHING,
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
    ts.add_host(hostname, ipaddress="127.0.0.1")
    config_cache = ts.apply(monkeypatch)

    agent_based_register.set_discovery_ruleset(
        RuleSetName("inventory_df_rules"),
        list[RuleSpec[dict[str, list[str]]]](
            [
                {
                    "id": "nobody-cares-about-the-id-in-this-test",
                    "value": {
                        "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
                        "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
                    },
                    "condition": {"host_labels": {"cmk/check_mk_server": "yes"}},
                }
            ]
        ),
    )
    DiscoveredHostLabelsStore(hostname).save(
        {
            "existing_label": {
                "plugin_name": "foo",
                "value": "bar",
            },
            "another_label": {
                "plugin_name": "labels",
                "value": "true",
            },
        }
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
                ),
                section_plugins={
                    section_name: agent_based_register.get_section_plugin(section_name)
                    for section_name in (SectionName("labels"), SectionName("df"))
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
def _cluster_scenario(monkeypatch) -> ClusterScenario:  # type:ignore[no-untyped-def]
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
                "condition": {
                    "service_description": [{"$regex": "fs_"}],
                    "host_name": [node1_hostname],
                },
                "value": True,
            }
        ],
    )
    config_cache = ts.apply(monkeypatch)

    agent_based_register.set_discovery_ruleset(
        RuleSetName("inventory_df_rules"),
        list[RuleSpec[dict[str, list[str]]]](
            [
                {
                    "id": "nobody-cares-about-the-id-in-this-test",
                    "value": {
                        "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
                        "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
                    },
                    "condition": {"host_labels": {"cmk/check_mk_server": "yes"}},
                }
            ]
        ),
    )
    DiscoveredHostLabelsStore(node1_hostname).save(
        {
            "node1_existing_label": {
                "plugin_name": "node1_plugin",
                "value": "true",
            }
        }
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
                ),
                section_plugins={
                    section_name: agent_based_register.get_section_plugin(section_name)
                    for section_name in (SectionName("labels"), SectionName("df"))
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
                ),
                section_plugins={
                    section_name: agent_based_register.get_section_plugin(section_name)
                    for section_name in (SectionName("labels"), SectionName("df"))
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


class ExpectedDiscoveryResultRealHost(NamedTuple):
    expected_vanished_host_labels: Sequence[HostLabel]
    expected_old_host_labels: Sequence[HostLabel]
    expected_new_host_labels: Sequence[HostLabel]
    expected_stored_labels: dict


class ExpectedDiscoveryResultCluster(NamedTuple):
    expected_vanished_host_labels: Sequence[HostLabel]
    expected_old_host_labels: Sequence[HostLabel]
    expected_new_host_labels: Sequence[HostLabel]
    expected_stored_labels_node1: dict
    expected_stored_labels_node2: dict


class DiscoveryTestCase(NamedTuple):
    load_labels: bool
    save_labels: bool
    only_host_labels: bool
    expected_services: set[tuple[CheckPluginName, str]]
    on_realhost: ExpectedDiscoveryResultRealHost
    on_cluster: ExpectedDiscoveryResultCluster


_discovery_test_cases = [
    # do discovery: only_new == True
    # discover on host: mode != "remove"
    DiscoveryTestCase(
        load_labels=True,
        save_labels=True,
        only_host_labels=False,
        expected_services={
            (CheckPluginName("df"), "/boot/test-efi"),
            (CheckPluginName("df"), "/opt/omd/sites/test-heute/tmp"),
        },
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_vanished_host_labels=[
                HostLabel("existing_label", "bar", SectionName("foo")),
                HostLabel("another_label", "true", SectionName("labels")),
            ],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
            ],
            expected_stored_labels={
                "cmk/check_mk_server": {
                    "plugin_name": "labels",
                    "value": "yes",
                },
            },
        ),
        on_cluster=ExpectedDiscoveryResultCluster(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                HostLabel("node2_live_label", "true", SectionName("labels")),
            ],
            expected_stored_labels_node1={
                "cmk/check_mk_server": {
                    "plugin_name": "labels",
                    "value": "yes",
                },
                "node1_existing_label": {
                    "plugin_name": "node1_plugin",
                    "value": "true",
                },
            },
            expected_stored_labels_node2={
                "node2_live_label": {
                    "plugin_name": "labels",
                    "value": "true",
                },
            },
        ),
    ),
    # check discovery
    DiscoveryTestCase(
        load_labels=True,
        save_labels=False,
        only_host_labels=False,
        expected_services={
            (CheckPluginName("df"), "/boot/test-efi"),
        },
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_vanished_host_labels=[
                HostLabel("existing_label", "bar", SectionName("foo")),
                HostLabel("another_label", "true", SectionName("labels")),
            ],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
            ],
            expected_stored_labels={
                "another_label": {
                    "plugin_name": "labels",
                    "value": "true",
                },
                "existing_label": {
                    "plugin_name": "foo",
                    "value": "bar",
                },
            },
        ),
        on_cluster=ExpectedDiscoveryResultCluster(
            expected_vanished_host_labels=[
                HostLabel("node1_existing_label", "true", SectionName("node1_plugin"))
            ],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                HostLabel("node2_live_label", "true", SectionName("labels")),
            ],
            expected_stored_labels_node1={
                "node1_existing_label": {
                    "plugin_name": "node1_plugin",
                    "value": "true",
                },
            },
            expected_stored_labels_node2={},
        ),
    ),
    # do discovery: only_new == False
    DiscoveryTestCase(
        load_labels=False,
        save_labels=True,
        only_host_labels=False,
        expected_services={
            (CheckPluginName("df"), "/boot/test-efi"),
            (CheckPluginName("df"), "/opt/omd/sites/test-heute/tmp"),
        },
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
            ],
            expected_stored_labels={
                "cmk/check_mk_server": {
                    "plugin_name": "labels",
                    "value": "yes",
                },
            },
        ),
        on_cluster=ExpectedDiscoveryResultCluster(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                HostLabel("node2_live_label", "true", SectionName("labels")),
            ],
            expected_stored_labels_node1={
                "cmk/check_mk_server": {
                    "plugin_name": "labels",
                    "value": "yes",
                },
            },
            expected_stored_labels_node2={
                "node2_live_label": {
                    "plugin_name": "labels",
                    "value": "true",
                },
            },
        ),
    ),
    # discover on host: mode == "remove"
    # do discovery: only_new == False
    # preview
    DiscoveryTestCase(
        load_labels=False,
        save_labels=False,
        only_host_labels=False,
        expected_services={
            (CheckPluginName("df"), "/boot/test-efi"),
        },
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
            ],
            expected_stored_labels={
                "another_label": {
                    "plugin_name": "labels",
                    "value": "true",
                },
                "existing_label": {
                    "plugin_name": "foo",
                    "value": "bar",
                },
            },
        ),
        on_cluster=ExpectedDiscoveryResultCluster(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                HostLabel("node2_live_label", "true", SectionName("labels")),
            ],
            expected_stored_labels_node1={
                "node1_existing_label": {
                    "plugin_name": "node1_plugin",
                    "value": "true",
                },
            },
            expected_stored_labels_node2={},
        ),
    ),
    # discover on host: mode == "only-host-labels"
    # Only discover host labels
    DiscoveryTestCase(
        load_labels=False,
        save_labels=False,
        only_host_labels=True,
        expected_services=set(),
        on_realhost=ExpectedDiscoveryResultRealHost(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
            ],
            expected_stored_labels={
                "another_label": {
                    "plugin_name": "labels",
                    "value": "true",
                },
                "existing_label": {
                    "plugin_name": "foo",
                    "value": "bar",
                },
            },
        ),
        on_cluster=ExpectedDiscoveryResultCluster(
            expected_vanished_host_labels=[],
            expected_old_host_labels=[],
            expected_new_host_labels=[
                HostLabel("cmk/check_mk_server", "yes", SectionName("labels")),
                HostLabel("node2_live_label", "true", SectionName("labels")),
            ],
            expected_stored_labels_node1={
                "node1_existing_label": {
                    "plugin_name": "node1_plugin",
                    "value": "true",
                },
            },
            expected_stored_labels_node2={},
        ),
    ),
]


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__discover_host_labels_and_services_on_realhost(
    realhost_scenario: RealHostScenario, discovery_test_case: DiscoveryTestCase
) -> None:
    if discovery_test_case.only_host_labels:
        # check for consistency of the test case
        assert not discovery_test_case.expected_services
        return

    scenario = realhost_scenario

    # We're depending on the changed host labels via the cache.
    if discovery_test_case.save_labels:
        analyse_host_labels(
            host_name=scenario.hostname,
            discovered_host_labels=discover_host_labels(
                scenario.hostname,
                HostLabelPluginMapper(),
                providers=scenario.providers,
                on_error=OnError.RAISE,
            ),
            ruleset_matcher=scenario.config_cache.ruleset_matcher,
            existing_host_labels=(
                do_load_labels(scenario.hostname) if discovery_test_case.load_labels else ()
            ),
            save_labels=discovery_test_case.save_labels,
        )

    discovered_services = discovery._discovered_services._discover_services(
        scenario.config_cache,
        scenario.hostname,
        providers=scenario.providers,
        check_plugins=CheckPluginMapper(),
        on_error=OnError.RAISE,
        run_plugin_names=EVERYTHING,
    )

    services = {s.id() for s in discovered_services}

    assert services == discovery_test_case.expected_services


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__perform_host_label_discovery_on_realhost(
    realhost_scenario: RealHostScenario, discovery_test_case: DiscoveryTestCase
) -> None:
    scenario = realhost_scenario

    host_label_result, _kept_labels = analyse_host_labels(
        host_name=scenario.hostname,
        discovered_host_labels=discover_host_labels(
            scenario.hostname,
            HostLabelPluginMapper(),
            providers=scenario.providers,
            on_error=OnError.RAISE,
        ),
        ruleset_matcher=scenario.config_cache.ruleset_matcher,
        existing_host_labels=(
            do_load_labels(scenario.hostname) if discovery_test_case.load_labels else ()
        ),
        save_labels=discovery_test_case.save_labels,
    )

    assert (
        host_label_result.vanished == discovery_test_case.on_realhost.expected_vanished_host_labels
    )
    assert host_label_result.old == discovery_test_case.on_realhost.expected_old_host_labels
    assert host_label_result.new == discovery_test_case.on_realhost.expected_new_host_labels

    assert (
        DiscoveredHostLabelsStore(scenario.hostname).load()
        == discovery_test_case.on_realhost.expected_stored_labels
    )


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__discover_services_on_cluster(
    cluster_scenario: ClusterScenario, discovery_test_case: DiscoveryTestCase
) -> None:
    if discovery_test_case.only_host_labels:
        # check for consistency of the test case
        assert not discovery_test_case.expected_services
        return

    if discovery_test_case.save_labels:
        return  # never called on cluster.

    scenario = cluster_scenario
    nodes = scenario.config_cache.nodes_of(scenario.parent)
    assert nodes is not None

    discovered_services = _get_cluster_services(
        scenario.parent,
        config_cache=scenario.config_cache,
        providers=scenario.providers,
        check_plugins=CheckPluginMapper(),
        find_service_description=config.service_description,
        on_error=OnError.RAISE,
    )

    services = set(discovered_services)

    assert services == discovery_test_case.expected_services


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize("discovery_test_case", _discovery_test_cases)
def test__perform_host_label_discovery_on_cluster(
    cluster_scenario: ClusterScenario, discovery_test_case: DiscoveryTestCase
) -> None:
    if discovery_test_case.save_labels:
        return  # never called on cluster.

    scenario = cluster_scenario
    nodes = scenario.config_cache.nodes_of(scenario.parent)
    assert nodes is not None

    host_label_result, _kept_labels = analyse_cluster_labels(
        scenario.parent,
        nodes,
        discovered_host_labels={
            node: discover_host_labels(
                node,
                HostLabelPluginMapper(),
                providers=scenario.providers,
                on_error=OnError.RAISE,
            )
            for node in nodes
        },
        existing_host_labels=(
            {node: do_load_labels(node) for node in nodes}
            if discovery_test_case.load_labels
            else {}
        ),
        ruleset_matcher=scenario.config_cache.ruleset_matcher,
    )

    assert (
        host_label_result.vanished == discovery_test_case.on_cluster.expected_vanished_host_labels
    )
    assert host_label_result.old == discovery_test_case.on_cluster.expected_old_host_labels
    assert host_label_result.new == discovery_test_case.on_cluster.expected_new_host_labels

    assert (
        DiscoveredHostLabelsStore(scenario.node1_hostname).load()
        == discovery_test_case.on_cluster.expected_stored_labels_node1
    )

    assert (
        DiscoveredHostLabelsStore(scenario.node2_hostname).load()
        == discovery_test_case.on_cluster.expected_stored_labels_node2
    )


def test_get_node_services(monkeypatch: MonkeyPatch) -> None:

    entries: Mapping[str, AutocheckEntry] = {
        discovery_status: AutocheckEntry(
            CheckPluginName(f"plugin_{discovery_status}"),
            None,
            {},
            {},
        )
        for discovery_status in (
            "old",
            "vanished",
            "new",
        )
    }

    monkeypatch.setattr(
        AutochecksStore,
        "read",
        lambda *args, **kwargs: [
            entries["old"],
            entries["vanished"],
        ],
    )

    monkeypatch.setattr(
        _discovered_services,
        "_discover_services",
        lambda *args, **kwargs: [
            entries["old"],
            entries["new"],
        ],
    )

    config_cache = Scenario().apply(monkeypatch)
    assert _get_node_services(
        config_cache,
        HostName("horst"),
        providers={},
        check_plugins={},
        find_service_description=lambda *_args: "desc",
        host_of_clustered_service=lambda hn, _svcdescr: hn,
        on_error=OnError.RAISE,
    ) == (
        {
            entry.id(): (
                discovery_status,
                entry,
                [HostName("horst")],
            )
            for discovery_status, entry in entries.items()
        },
        False,
    )


def test_make_discovery_diff_empty() -> None:
    assert _make_diff((), (), (), ()) == "Nothing was changed."


class _MockService(NamedTuple):
    check_plugin_name: CheckPluginName
    item: str | None


def test_make_discovery_diff() -> None:
    assert _make_diff(
        (HostLabel("foo", "bar"),),
        (HostLabel("gee", "boo"),),
        (_MockService(CheckPluginName("norris"), "chuck"),),  # type: ignore[arg-type]
        (_MockService(CheckPluginName("chan"), None),),  # type: ignore[arg-type]
    ) == (
        "Removed host label: 'foo:bar'.\n"
        "Added host label: 'gee:boo'.\n"
        "Removed service: Check plugin 'norris' / item 'chuck'.\n"
        "Added service: Check plugin 'chan'."
    )
