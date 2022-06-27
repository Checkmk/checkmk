#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.services as services
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state

STRING_TABLE = [
    ["wscsvc", "running/auto", "Security", "Center"],
    ["WSearch", "stopped/demand", "Windows", "Search"],
    ["wuauserv", "stopped/disabled", "Windows", "Update"],
    ["app", "pending", "Windows App", "Update"],
]

PARSED = [
    services.WinService("wscsvc", "running", "auto", "Security Center"),
    services.WinService("WSearch", "stopped", "demand", "Windows Search"),
    services.WinService("wuauserv", "stopped", "disabled", "Windows Update"),
    services.WinService("app", "pending", "unknown", "Windows App Update"),
]

PARSED_NODE = [
    services.WinService("wscsvc", "running", "auto", "Security Center"),
    services.WinService("WSearch", "stopped", "demand", "Windows Search"),
    services.WinService("wuauserv", "stopped", "disabled", "Windows Update"),
    services.WinService("app", "running", "unknown", "Windows App Update"),
]

PARSED_AUTO = [
    services.WinService("wscsvc", "running", "auto", "Security Center"),
    services.WinService("WSearch", "stopped", "demand", "Windows Search"),
    services.WinService("wuauserv", "stopped", "disabled", "Windows Update"),
    services.WinService("app", "stopped", "auto", "Windows App Update"),
]


def test_parse() -> None:
    assert PARSED == services.parse_windows_services(STRING_TABLE)


@pytest.mark.parametrize(
    "params, discovered_services",
    [
        (
            [services.WINDOWS_SERVICES_DISCOVERY_DEFAULT_PARAMETERS],
            [],
        ),
        (
            [
                {
                    "services": ["app*"],
                    "state": "pending",
                },
                services.WINDOWS_SERVICES_DISCOVERY_DEFAULT_PARAMETERS,
            ],
            [
                Service(item="app", parameters={}, labels=[]),
            ],
        ),
        (
            [
                {
                    "services": ["Windows*"],
                    "start_mode": "demand",
                },
                services.WINDOWS_SERVICES_DISCOVERY_DEFAULT_PARAMETERS,
            ],
            [
                Service(item="WSearch", parameters={}, labels=[]),
            ],
        ),
        (
            [
                {
                    "services": ["Windows*"],
                    "start_mode": "demand",
                    "state": "running",
                },
                services.WINDOWS_SERVICES_DISCOVERY_DEFAULT_PARAMETERS,
            ],
            [],
        ),
    ],
)
def test_discovery_windows_services(params, discovered_services) -> None:
    assert discovered_services == list(services.discovery_windows_services(params, PARSED))


@pytest.mark.parametrize(
    "item, params, yielded_results",
    [
        (
            "WSearch",
            services.WINDOWS_SERVICES_CHECK_DEFAULT_PARAMETERS,
            [
                Result(state=state.CRIT, summary="Windows Search: stopped (start type is demand)"),
            ],
        ),
        (
            "WSearch",
            {"else": 1},
            [
                Result(state=state.WARN, summary="Windows Search: stopped (start type is demand)"),
            ],
        ),
        (
            "WSearch",
            {"states": [("stopped", None, 0)]},
            [
                Result(state=state.OK, summary="Windows Search: stopped (start type is demand)"),
            ],
        ),
        (
            "WSearch",
            {"states": [(None, "demand", 1)]},
            [
                Result(state=state.WARN, summary="Windows Search: stopped (start type is demand)"),
            ],
        ),
        (
            "WSearch",
            {"additional_servicenames": ["wuauserv"]},
            [
                Result(state=state.CRIT, summary="Windows Search: stopped (start type is demand)"),
                Result(
                    state=state.CRIT, summary="Windows Update: stopped (start type is disabled)"
                ),
            ],
        ),
        (
            "WSearch",
            {
                "else": 0,
                "states": [],
            },
            [
                Result(state=state.OK, summary="Windows Search: stopped (start type is demand)"),
            ],
        ),
        (
            "NonExistent",
            {
                "states": [(None, "demand", 1)],
            },
            [
                Result(state=state.CRIT, summary="service not found"),
            ],
        ),
        (
            "NonExistent",
            {
                "states": [(None, "demand", 1)],
                "else": 0,
            },
            [
                Result(state=state.OK, summary="service not found"),
            ],
        ),
    ],
)
def test_check_windows_services(item, params, yielded_results) -> None:
    assert yielded_results == list(services.check_windows_services(item, params, PARSED))


@pytest.mark.parametrize(
    "item, params, yielded_results",
    [
        (
            "app",
            services.WINDOWS_SERVICES_CHECK_DEFAULT_PARAMETERS,
            [
                Result(
                    state=state.OK, summary="Windows App Update: running (start type is unknown)"
                ),
                Result(state=state.OK, summary="Running on: node2"),
            ],
        ),
        (
            "app",
            {"states": [("running", None, 2)]},
            [
                Result(
                    state=state.CRIT, summary="Windows App Update: running (start type is unknown)"
                ),
            ],
        ),
        (
            "non-existant-service",
            services.WINDOWS_SERVICES_CHECK_DEFAULT_PARAMETERS,
            [
                Result(state=state.CRIT, summary="service not found"),
            ],
        ),
    ],
)
def test_cluster_windows_services(item, params, yielded_results) -> None:
    assert yielded_results == list(
        services.cluster_check_windows_services(
            item, params, {"node1": PARSED, "node2": PARSED_NODE}
        )
    )


def test_discovery_services_summary() -> None:
    assert [Service()] == list(services.discovery_services_summary(PARSED))


@pytest.mark.parametrize(
    "params, yielded_results",
    [
        (
            services.SERVICES_SUMMARY_DEFAULT_PARAMETERS,
            [
                Result(
                    state=state.OK,
                    summary="Autostart services: 2",
                    details="Autostart services: 2\nServices found in total: 4",
                ),
                Result(
                    state=state.OK,
                    summary="Stopped services: 1",
                    details="Stopped services: app",
                ),
            ],
        ),
        (
            {"state_if_stopped": 2},
            [
                Result(
                    state=state.OK,
                    summary="Autostart services: 2",
                    details="Autostart services: 2\nServices found in total: 4",
                ),
                Result(
                    state=state.CRIT,
                    summary="Stopped services: 1",
                    details="Stopped services: app",
                ),
            ],
        ),
        (
            {"ignored": ["app"]},
            [
                Result(
                    state=state.OK,
                    summary="Autostart services: 2",
                    details="Autostart services: 2\nServices found in total: 4",
                ),
                Result(
                    state=state.OK,
                    summary="Stopped services: 0",
                    details="Stopped services: 0",
                ),
                Result(
                    state=state.OK,
                    notice="Stopped but ignored: 1",
                ),
            ],
        ),
    ],
)
def test_check_services_summary(params, yielded_results) -> None:
    assert yielded_results == list(services.check_services_summary(params, PARSED_AUTO))
