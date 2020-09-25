#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import pytest  # type: ignore[import]
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Service,
    State as state,
    Result,
)
import cmk.base.plugins.agent_based.services as services

STRING_TABLE = [
    ['wscsvc', 'running/auto', 'Security', 'Center'],
    ['WSearch', 'stopped/demand', 'Windows', 'Search'],
    ['wuauserv', 'stopped/disabled', 'Windows', 'Update'],
    ['app', 'pending', 'Windows App', 'Update'],
]

PARSED = {
    'WSearch': {
        'description': 'Windows Search',
        'start_type': 'demand',
        'state': 'stopped'
    },
    'app': {
        'description': 'Windows App Update',
        'start_type': 'unknown',
        'state': 'pending'
    },
    'wscsvc': {
        'description': 'Security Center',
        'start_type': 'auto',
        'state': 'running'
    },
    'wuauserv': {
        'description': 'Windows Update',
        'start_type': 'disabled',
        'state': 'stopped'
    },
}

PARSED_NODE = copy.deepcopy(PARSED)
PARSED_NODE["app"] = {
    'description': 'Windows App Update',
    'start_type': 'unknown',
    'state': 'running'
}

PARSED_AUTO = copy.deepcopy(PARSED)
PARSED_AUTO["app"] = {'description': 'Windows App Update', 'start_type': 'auto', 'state': 'stopped'}


def test_parse():
    assert PARSED == services.parse_windows_services(STRING_TABLE)


@pytest.mark.parametrize("params, discovered_services", [
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
            Service(item='app', parameters={}, labels=[]),
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
            Service(item='WSearch', parameters={}, labels=[]),
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
])
def test_discovery_windows_services(params, discovered_services):
    assert discovered_services == list(services.discovery_windows_services(params, PARSED))


@pytest.mark.parametrize("item, params, yielded_results", [
    ("WSearch", services.WINDOWS_SERVICES_CHECK_DEFAULT_PARAMETERS, [
        Result(state=state.CRIT,
               summary='Windows Search: stopped (start type is demand)',
               details='Windows Search: stopped (start type is demand)')
    ]),
    ("WSearch", {
        "else": 1
    }, [
        Result(state=state.WARN,
               summary='Windows Search: stopped (start type is demand)',
               details='Windows Search: stopped (start type is demand)')
    ]),
    ("WSearch", {
        "states": [("stopped", None, 0)]
    }, [
        Result(state=state.OK,
               summary='Windows Search: stopped (start type is demand)',
               details='Windows Search: stopped (start type is demand)')
    ]),
    ("WSearch", {
        "states": [(None, "demand", 1)]
    }, [
        Result(state=state.WARN,
               summary='Windows Search: stopped (start type is demand)',
               details='Windows Search: stopped (start type is demand)')
    ]),
    ("WSearch", {
        "additional_servicenames": ["wuauserv"]
    }, [
        Result(state=state.CRIT,
               summary='Windows Search: stopped (start type is demand)',
               details='Windows Search: stopped (start type is demand)'),
        Result(state=state.CRIT,
               summary='Windows Update: stopped (start type is disabled)',
               details='Windows Update: stopped (start type is disabled)')
    ]),
])
def test_check_windows_services(item, params, yielded_results):
    assert yielded_results == list(services.check_windows_services(item, params, PARSED))


@pytest.mark.parametrize("item, params, yielded_results", [
    ("app", services.WINDOWS_SERVICES_CHECK_DEFAULT_PARAMETERS, [
        Result(state=state.OK,
               summary='Windows App Update: running (start type is unknown)',
               details='Windows App Update: running (start type is unknown)'),
        Result(state=state.OK, summary='Running on: node2', details='Running on: node2')
    ]),
    ("app", {
        "states": [("running", None, 2)]
    }, [
        Result(state=state.CRIT,
               summary='Windows App Update: running (start type is unknown)',
               details='Windows App Update: running (start type is unknown)'),
    ]),
    ("non-existant-service", services.WINDOWS_SERVICES_CHECK_DEFAULT_PARAMETERS, [
        Result(state=state.CRIT, summary='service not found', details='service not found'),
    ]),
])
def test_cluster_windows_services(item, params, yielded_results):
    assert yielded_results == list(
        services.cluster_check_windows_services(item, params, {
            "node1": PARSED,
            "node2": PARSED_NODE
        }))


def test_discovery_services_summary():
    assert [Service()] == list(services.discovery_services_summary(PARSED))


@pytest.mark.parametrize("params, yielded_results", [
    (services.SERVICES_SUMMARY_DEFAULT_PARAMETERS, [
        Result(
            state=state.OK,
            summary=
            '4 services, 2 services in autostart - of which 1 services are stopped (app), 0 services stopped but ignored',
            details=
            '4 services, 2 services in autostart - of which 1 services are stopped (app), 0 services stopped but ignored'
        )
    ]),
    ({
        "state_if_stopped": 2
    }, [
        Result(
            state=state.CRIT,
            summary=
            '4 services, 2 services in autostart - of which 1 services are stopped (app), 0 services stopped but ignored',
            details=
            '4 services, 2 services in autostart - of which 1 services are stopped (app), 0 services stopped but ignored'
        )
    ]),
    ({
        "ignored": ["app"]
    }, [
        Result(
            state=state.OK,
            summary=
            '4 services, 2 services in autostart - of which 0 services are stopped, 1 services stopped but ignored',
            details=
            '4 services, 2 services in autostart - of which 0 services are stopped, 1 services stopped but ignored'
        )
    ]),
])
def test_check_services_summary(params, yielded_results):
    assert yielded_results == list(services.check_services_summary(params, PARSED_AUTO))
