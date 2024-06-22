#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.servicename import ServiceName

from cmk.checkengine.checking import (
    AggregatedResult,
    check_plugins_missing_data,
    CheckPluginName,
    ConfiguredService,
)
from cmk.checkengine.checkresults import UnsubmittableServiceCheckResult
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.parameters import TimespecificParameters


def _service(plugin: str, item: str | None) -> ConfiguredService:
    return ConfiguredService(
        check_plugin_name=CheckPluginName(plugin),
        item=item,
        description=f"test description {plugin}/{item}",
        parameters=TimespecificParameters(),
        discovered_parameters={},
        service_labels={},
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
            service_labels={},
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
