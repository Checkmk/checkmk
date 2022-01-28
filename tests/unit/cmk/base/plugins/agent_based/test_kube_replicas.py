#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from typing import Any, Mapping, MutableMapping, Sequence, Union

import pytest

import cmk.base.plugins.agent_based.kube_replicas as kube_replicas
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.kube_replicas import (
    check_kube_replicas,
    discover_kube_replicas,
    parse_kube_deployment_spec,
    parse_kube_replicas,
)
from cmk.base.plugins.agent_based.utils.k8s import (
    DeploymentSpec,
    Replicas,
    RollingUpdate,
    UpdateStrategy,
)


def test_parse_kube_replicas() -> None:
    assert parse_kube_replicas(
        [
            [
                json.dumps(
                    {
                        "replicas": 3,
                        "updated": 0,
                        "available": 0,
                        "ready": 3,
                        "unavailable": 0,
                    }
                )
            ]
        ]
    ) == Replicas(
        replicas=3,
        updated=0,
        available=0,
        ready=3,
        unavailable=0,
    )


def test_parse_kube_deployment_spec() -> None:
    assert parse_kube_deployment_spec(
        [
            [
                json.dumps(
                    {
                        "strategy": {
                            "type_": "RollingUpdate",
                            "rolling_update": {"max_surge": "25%", "max_unavailable": "25%"},
                        },
                    }
                )
            ]
        ]
    ) == DeploymentSpec(
        strategy=UpdateStrategy(
            type_="RollingUpdate",
            rolling_update=RollingUpdate(max_surge="25%", max_unavailable="25%"),
        )
    )

    assert parse_kube_deployment_spec(
        [
            [
                json.dumps(
                    {
                        "strategy": {
                            "type_": "Recreate",
                            "rolling_update": None,
                        },
                    }
                )
            ]
        ]
    ) == DeploymentSpec(
        strategy=UpdateStrategy(
            type_="Recreate",
            rolling_update=None,
        )
    )


def test_discover_kube_replicas() -> None:
    replicas = Replicas(
        replicas=3,
        updated=0,
        available=0,
        ready=3,
        unavailable=3,
    )
    spec = DeploymentSpec(
        strategy=UpdateStrategy(
            type_="RollingUpdate",
            rolling_update=RollingUpdate(max_surge="25%", max_unavailable="25%"),
        )
    )
    assert list(discover_kube_replicas(replicas, spec)) == [Service()]
    assert list(discover_kube_replicas(replicas, None)) == [Service()]
    assert list(discover_kube_replicas(None, spec)) == []
    assert list(discover_kube_replicas(None, None)) == []


def test_check_kube_replicas() -> None:
    assert list(
        check_kube_replicas(
            {},
            Replicas(
                replicas=3,
                updated=3,
                available=3,
                ready=3,
                unavailable=0,
            ),
            None,
        )
    ) == [
        Result(state=State.OK, summary="Ready: 3/3"),
        Result(state=State.OK, summary="Up-to-date: 3/3"),
        Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
        Metric("kube_ready_replicas", 3.0, boundaries=(0.0, 3.0)),
        Metric("kube_updated_replicas", 3.0, boundaries=(0.0, 3.0)),
    ]


@pytest.mark.parametrize(
    "params,replicas,spec,value_store,expected_check_result",
    [
        pytest.param(
            {"update_duration": "no_levels"},
            Replicas(
                replicas=3,
                updated=0,
                available=3,
                ready=3,
                unavailable=0,
            ),
            DeploymentSpec(
                strategy=UpdateStrategy(
                    type_="RollingUpdate",
                    rolling_update=RollingUpdate(max_surge="25%", max_unavailable="25%"),
                )
            ),
            {"update_started_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 3/3"),
                Result(state=State.OK, summary="Up-to-date: 0/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 0.0, boundaries=(0.0, 3.0)),
                Result(state=State.OK, summary="Not updated for: 11 minutes 40 seconds"),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max surge: 25%, max unavailable: 25%)",
                ),
            ],
            id="Out-of-date replicas is OK when no parameters are specified, update strategy is shown",
        ),
        pytest.param(
            {"update_duration": ("levels", (900, 1000))},
            Replicas(
                replicas=3,
                updated=0,
                available=3,
                ready=3,
                unavailable=0,
            ),
            DeploymentSpec(
                strategy=UpdateStrategy(
                    type_="RollingUpdate",
                    rolling_update=RollingUpdate(max_surge="25%", max_unavailable="25%"),
                )
            ),
            {"update_started_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 3/3"),
                Result(state=State.OK, summary="Up-to-date: 0/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 0.0, boundaries=(0.0, 3.0)),
                Result(state=State.OK, summary="Not updated for: 11 minutes 40 seconds"),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max surge: 25%, max unavailable: 25%)",
                ),
            ],
            id="Out-of-date replicas is OK when thresholds are not reached, update strategy is shown",
        ),
        pytest.param(
            {"update_duration": ("levels", (300, 500))},
            Replicas(
                replicas=3,
                updated=0,
                available=3,
                ready=3,
                unavailable=0,
            ),
            DeploymentSpec(
                strategy=UpdateStrategy(
                    type_="RollingUpdate",
                    rolling_update=RollingUpdate(max_surge="25%", max_unavailable="25%"),
                )
            ),
            {"update_started_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 3/3"),
                Result(state=State.OK, summary="Up-to-date: 0/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 0.0, boundaries=(0.0, 3.0)),
                Result(
                    state=State.CRIT,
                    summary="Not updated for: 11 minutes 40 seconds (warn/crit at 5 minutes 0 seconds/8 minutes 20 seconds)",
                ),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max surge: 25%, max unavailable: 25%)",
                ),
            ],
            id="Out-of-date replicas thresholds are applied, update strategy is shown",
        ),
    ],
)
def test_check_kube_replicas_outdated_replicas(
    params: Mapping[str, Any],
    replicas: Replicas,
    spec: DeploymentSpec,
    value_store: MutableMapping[str, Any],
    expected_check_result: Sequence[Union[Result, Metric]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_value_store():
        return value_store

    def mock_time():
        return 800.0

    monkeypatch.setattr(kube_replicas, "get_value_store", mock_value_store)
    monkeypatch.setattr(time, "time", mock_time)

    assert list(check_kube_replicas(params, replicas, spec)) == expected_check_result


@pytest.mark.parametrize(
    "params,replicas,value_store,expected_check_result",
    [
        pytest.param(
            {"not_ready_duration": "no_levels"},
            Replicas(
                replicas=3,
                updated=3,
                available=3,
                ready=0,
                unavailable=0,
            ),
            {"not_ready_started_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 0/3"),
                Result(state=State.OK, summary="Up-to-date: 3/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 0.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 3.0, boundaries=(0.0, 3.0)),
                Result(state=State.OK, summary="Not ready for: 11 minutes 40 seconds"),
            ],
            id="Not ready replicas is OK when no parameters are specified, update strategy is not shown",
        ),
        pytest.param(
            {"not_ready_duration": ("levels", (900, 1000))},
            Replicas(
                replicas=3,
                updated=3,
                available=3,
                ready=0,
                unavailable=0,
            ),
            {"not_ready_started_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 0/3"),
                Result(state=State.OK, summary="Up-to-date: 3/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 0.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 3.0, boundaries=(0.0, 3.0)),
                Result(state=State.OK, summary="Not ready for: 11 minutes 40 seconds"),
            ],
            id="Not ready replicas is OK when thresholds are not reached, update strategy is not shown",
        ),
        pytest.param(
            {"not_ready_duration": ("levels", (300, 500))},
            Replicas(
                replicas=3,
                updated=3,
                available=3,
                ready=0,
                unavailable=0,
            ),
            {"not_ready_started_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 0/3"),
                Result(state=State.OK, summary="Up-to-date: 3/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 0.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 3.0, boundaries=(0.0, 3.0)),
                Result(
                    state=State.CRIT,
                    summary="Not ready for: 11 minutes 40 seconds (warn/crit at 5 minutes 0 seconds/8 minutes 20 seconds)",
                ),
            ],
            id="Not ready replicas thresholds are applied, update strategy is shown",
        ),
    ],
)
def test_check_kube_replicas_not_ready_replicas(
    params: Mapping[str, Any],
    replicas: Replicas,
    value_store: MutableMapping[str, Any],
    expected_check_result: Sequence[Union[Result, Metric]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_value_store():
        return value_store

    def mock_time():
        return 800.0

    monkeypatch.setattr(kube_replicas, "get_value_store", mock_value_store)
    monkeypatch.setattr(time, "time", mock_time)

    assert list(check_kube_replicas(params, replicas, None)) == expected_check_result


@pytest.mark.parametrize(
    "params,replicas,spec,value_store,expected_check_result",
    [
        pytest.param(
            {
                "not_ready_duration": ("levels", (300, 500)),
                "update_duration": ("levels", (300, 500)),
            },
            Replicas(
                replicas=3,
                updated=0,
                available=3,
                ready=0,
                unavailable=0,
            ),
            DeploymentSpec(
                strategy=UpdateStrategy(
                    type_="RollingUpdate",
                    rolling_update=RollingUpdate(max_surge="25%", max_unavailable="25%"),
                )
            ),
            {"not_ready_started_timestamp": 100.0, "update_started_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 0/3"),
                Result(state=State.OK, summary="Up-to-date: 0/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 0.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 0.0, boundaries=(0.0, 3.0)),
                Result(
                    state=State.CRIT,
                    summary="Not ready for: 11 minutes 40 seconds (warn/crit at 5 minutes 0 seconds/8 minutes 20 seconds)",
                ),
                Result(
                    state=State.CRIT,
                    summary="Not updated for: 11 minutes 40 seconds (warn/crit at 5 minutes 0 seconds/8 minutes 20 seconds)",
                ),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max surge: 25%, max unavailable: 25%)",
                ),
            ],
            id="Not ready and outdated replicas are both checked and shown",
        ),
    ],
)
def test_check_kube_replicas_not_ready_and_outdated(
    params: Mapping[str, Any],
    replicas: Replicas,
    spec: DeploymentSpec,
    value_store: MutableMapping[str, Any],
    expected_check_result: Sequence[Union[Result, Metric]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_value_store():
        return value_store

    def mock_time():
        return 800.0

    monkeypatch.setattr(kube_replicas, "get_value_store", mock_value_store)
    monkeypatch.setattr(time, "time", mock_time)

    assert list(check_kube_replicas(params, replicas, spec)) == expected_check_result


@pytest.mark.parametrize(
    "params,replicas,value_store,expected_check_result",
    [
        pytest.param(
            {
                "not_ready_duration": ("levels", (300, 500)),
                "update_duration": ("levels", (300, 500)),
            },
            Replicas(
                replicas=3,
                updated=0,
                available=3,
                ready=3,
                unavailable=0,
            ),
            {"not_ready_started_timestamp": 100.0, "update_started_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 3/3"),
                Result(state=State.OK, summary="Up-to-date: 0/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 0.0, boundaries=(0.0, 3.0)),
                Result(
                    state=State.CRIT,
                    summary="Not updated for: 11 minutes 40 seconds (warn/crit at 5 minutes 0 seconds/8 minutes 20 seconds)",
                ),
            ],
            id="Restored ready condition resets value store and leads to OK check result",
        ),
        pytest.param(
            {
                "not_ready_duration": ("levels", (300, 500)),
                "update_duration": ("levels", (300, 500)),
            },
            Replicas(
                replicas=3,
                updated=3,
                available=3,
                ready=0,
                unavailable=0,
            ),
            {"not_ready_started_timestamp": 100.0, "update_started_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 0/3"),
                Result(state=State.OK, summary="Up-to-date: 3/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 0.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 3.0, boundaries=(0.0, 3.0)),
                Result(
                    state=State.CRIT,
                    summary="Not ready for: 11 minutes 40 seconds (warn/crit at 5 minutes 0 seconds/8 minutes 20 seconds)",
                ),
            ],
            id="Restored up-to-date condition resets value store and leads to OK check result",
        ),
    ],
)
def test_check_kube_replicas_value_store_reset(
    params: Mapping[str, Any],
    replicas: Replicas,
    value_store: MutableMapping[str, Any],
    expected_check_result: Sequence[Union[Result, Metric]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_value_store():
        return value_store

    def mock_time():
        return 800.0

    monkeypatch.setattr(kube_replicas, "get_value_store", mock_value_store)
    monkeypatch.setattr(time, "time", mock_time)

    assert list(check_kube_replicas(params, replicas, None)) == expected_check_result
