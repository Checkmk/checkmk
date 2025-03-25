#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.utils.hostaddress import HostAddress
from cmk.utils.servicename import ServiceName

from cmk.checkengine.checking import (
    check_plugins_missing_data,
    merge_enforced_services,
    ServiceConfigurer,
)
from cmk.checkengine.checkresults import UnsubmittableServiceCheckResult
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.plugins import (
    AggregatedResult,
    CheckPluginName,
    ConfiguredService,
    ServiceID,
)


def _service(plugin: str, item: str | None) -> ConfiguredService:
    return ConfiguredService(
        check_plugin_name=CheckPluginName(plugin),
        item=item,
        description=f"test description {plugin}/{item}",
        parameters=TimespecificParameters(),
        discovered_parameters={},
        discovered_labels={},
        labels={},
        is_enforced=False,
    )


def test_service_sortable() -> None:
    assert sorted(
        [
            _service("B", "b"),
            _service("A", "b"),
            _service("B", "a"),
            _service("A", None),
        ],
        key=lambda s: s.sort_key(),
    ) == [
        _service("A", None),
        _service("A", "b"),
        _service("B", "a"),
        _service("B", "b"),
    ]


def make_aggregated_result(*, name: str, data_received: bool) -> AggregatedResult:
    return AggregatedResult(
        service=ConfiguredService(
            check_plugin_name=CheckPluginName(name),
            item=None,
            description=ServiceName("ut_service_name"),
            parameters=TimespecificParameters(),
            discovered_parameters={},
            discovered_labels={},
            labels={},
            is_enforced=False,
        ),
        data_received=data_received,
        result=UnsubmittableServiceCheckResult(),
        cache_info=None,
    )


def test_missing_data_single() -> None:
    # we want to map a specific service with a certain service name to be OK, although data is
    # missing:
    # create rule "Status of the Checkmk service"
    # check "State if specific check plug-ins receive no monitoring data"
    # specify regex "not$" and "OK"

    assert [
        (r.state, r.summary)
        for r in check_plugins_missing_data(
            [
                make_aggregated_result(name="not", data_received=False),
                # we need an additional service, otherwise we will go the "Missing monitoring data for all
                # plugins" special case ( see below)
                make_aggregated_result(name="data_received", data_received=True),
            ],
            ExitSpec(specific_missing_sections=[("not$", 0)]),
            # this is a bug: we miss data for a single plug-in (not), mapped this plug-in to be
            # ok, but in summary we return a warning:
        )
    ] == [
        (0, "Missing monitoring data for plugins"),
        (0, "not"),
    ]


def test_missing_data_all() -> None:
    assert [
        (r.state, r.summary)
        for r in check_plugins_missing_data(
            [
                make_aggregated_result(name="unknown", data_received=False),
            ],
            ExitSpec(),
        )
    ] == [
        (1, "Missing monitoring data for all plugins"),
    ]


def _get_aggregated_results() -> list[AggregatedResult]:
    return [
        make_aggregated_result(name="not_1", data_received=False),
        make_aggregated_result(name="not_2", data_received=False),
        make_aggregated_result(name="not_3", data_received=False),
        make_aggregated_result(name="data_received", data_received=True),
    ]


def test_missing_data_default_config() -> None:
    assert [
        (r.state, r.summary)
        for r in check_plugins_missing_data(
            _get_aggregated_results(),
            ExitSpec(),
        )
    ] == [
        (0, "Missing monitoring data for plugins"),
        (1, "not_1"),
        (1, "not_2"),
        (1, "not_3"),
    ]


def test_missing_data_regex() -> None:
    assert [
        (r.state, r.summary)
        for r in check_plugins_missing_data(
            _get_aggregated_results(),
            ExitSpec(specific_missing_sections=[("not_2$", 3)]),
        )
    ] == [
        (0, "Missing monitoring data for plugins"),
        (1, "not_1"),
        (3, "not_2"),
        (1, "not_3"),
    ]


def test_missing_data_regex_and_default() -> None:
    assert [
        (r.state, r.summary)
        for r in check_plugins_missing_data(
            _get_aggregated_results(),
            ExitSpec(specific_missing_sections=[("not_2$", 3)], missing_sections=0),
        )
    ] == [
        (0, "Missing monitoring data for plugins"),
        (0, "not_1"),
        (3, "not_2"),
        (0, "not_3"),
    ]


@dataclass
class AutocheckEntryLike:
    check_plugin_name: CheckPluginName
    item: str | None
    parameters: Mapping[str, str]
    service_labels: Mapping[str, str]


def test_service_configurer() -> None:
    _COMPUTED_PARAMETERS_SENTINEL = TimespecificParameters(())

    service_configurer = ServiceConfigurer(
        compute_check_parameters=lambda *a: _COMPUTED_PARAMETERS_SENTINEL,
        get_service_description=lambda _host, check, item: f"{check}-{item}",
        get_effective_host=lambda host, _desc, _labels: host,
        get_service_labels=lambda _host, _desc, labels: labels,
    )

    assert (
        result := service_configurer.configure_autochecks(
            HostAddress("somehost"), [AutocheckEntryLike(CheckPluginName("df"), "/", {}, {})]
        )
    ) == [
        ConfiguredService(
            check_plugin_name=CheckPluginName("df"),
            item="/",
            description="df-/",  # we pass a simple callback, not the real one!
            parameters=_COMPUTED_PARAMETERS_SENTINEL,
            discovered_parameters={},
            discovered_labels={},
            labels={},
            is_enforced=False,
        ),
    ]
    # see that compute_check_parameters has been called:
    assert result[0].parameters is _COMPUTED_PARAMETERS_SENTINEL


def _dummy_service(sid: ServiceID) -> ConfiguredService:
    return ConfiguredService(*sid, "", TimespecificParameters(), {}, {}, {}, True)


def test_aggregate_enforced_services_filters_unclustered() -> None:
    sid1 = ServiceID(CheckPluginName("check1"), None)
    sid2 = ServiceID(CheckPluginName("check2"), None)
    assert tuple(
        merge_enforced_services(
            {
                HostAddress("host1"): {sid1: ("ruleset_name1", _dummy_service(sid1))},
                HostAddress("host2"): {sid2: ("ruleset_name2", _dummy_service(sid2))},
            },
            lambda host_name, servic_name, discovered_labels: host_name == HostAddress("host1"),
            lambda service_name, discovered_labels: discovered_labels,
        )
    ) == (_dummy_service(sid1),)


def _make_params(raw: Mapping[str, object]) -> TimespecificParameters:
    return TimespecificParameters((TimespecificParameterSet.from_parameters(raw),))


def test_aggregate_enforced_services_merge() -> None:
    sid = ServiceID(CheckPluginName("check"), None)
    assert tuple(
        merge_enforced_services(
            {
                HostAddress("host1"): {
                    sid: (
                        "ruleset_name",
                        ConfiguredService(
                            *sid,
                            "Description",
                            _make_params({"common": 1, "1": 1}),
                            {"common": 1, "1": 1},
                            {"common": "1", "1": "1"},
                            {"common": "1", "1": "1"},
                            True,
                        ),
                    )
                },
                HostAddress("host2"): {
                    sid: (
                        "ruleset_name",
                        ConfiguredService(
                            *sid,
                            "Description",
                            _make_params({"common": 2, "2": 2}),
                            {"common": 2, "2": 2},
                            {"common": "2", "2": "2"},
                            {"common": "2", "2": "2"},
                            True,
                        ),
                    )
                },
            },
            lambda host_name, servic_name, discovered_labels: True,
            lambda service_name, discovered_labels: discovered_labels,
        )
    ) == (
        ConfiguredService(
            *sid,
            "Description",
            TimespecificParameters(
                (
                    TimespecificParameterSet.from_parameters({"common": 1, "1": 1}),
                    TimespecificParameterSet.from_parameters({"common": 2, "2": 2}),
                )
            ),
            {"common": 1, "1": 1, "2": 2},
            {"common": "1", "1": "1", "2": "2"},
            {"common": "1", "1": "1", "2": "2"},
            is_enforced=True,
        ),
    )
