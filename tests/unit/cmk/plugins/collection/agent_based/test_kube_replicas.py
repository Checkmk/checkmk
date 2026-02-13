#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based import kube_replicas
from cmk.plugins.collection.agent_based.kube_replicas import (
    _check_kube_replicas,
    check_kube_replicas,
    discover_kube_replicas,
    parse_kube_daemonset_replicas,
    parse_kube_deployment_replicas,
    parse_kube_statefulset_replicas,
    parse_kube_strategy,
    Replicas,
)
from cmk.plugins.kube.schemata.api import (
    OnDelete,
    Recreate,
    RollingUpdate,
    StatefulSetRollingUpdate,
)
from cmk.plugins.kube.schemata.section import (
    ControllerSpec,
    DaemonSetReplicas,
    DeploymentReplicas,
    StatefulSetReplicas,
    UpdateStrategy,
)
from cmk.plugins.lib.kube import VSResultAge


def test_parse_kube_deployment_replicas() -> None:
    assert parse_kube_deployment_replicas(
        [
            [
                json.dumps(
                    {
                        "available": 3,
                        "desired": 3,
                        "updated": 0,
                        "ready": 3,
                    }
                )
            ]
        ]
    ) == DeploymentReplicas(
        available=3,
        desired=3,
        updated=0,
        ready=3,
    )


def test_parse_kube_statefulset_replicas() -> None:
    assert parse_kube_statefulset_replicas(
        [
            [
                json.dumps(
                    {
                        "available": 3,
                        "desired": 3,
                        "updated": 0,
                        "ready": 3,
                    }
                )
            ]
        ]
    ) == StatefulSetReplicas(
        available=3,
        desired=3,
        updated=0,
        ready=3,
    )


def test_parse_kube_daemonset_replicas() -> None:
    assert parse_kube_daemonset_replicas(
        [
            [
                json.dumps(
                    {
                        "available": 3,
                        "desired": 3,
                        "updated": 0,
                        "ready": 3,
                        "misscheduled": 2,
                    }
                )
            ]
        ]
    ) == DaemonSetReplicas(
        available=3,
        desired=3,
        updated=0,
        ready=3,
        misscheduled=2,
    )


def test_parse_kube_strategy() -> None:
    assert parse_kube_strategy(
        [
            [
                json.dumps(
                    {
                        "strategy": {
                            "type_": "RollingUpdate",
                            "max_surge": "25%",
                            "max_unavailable": "25%",
                        }
                    }
                )
            ]
        ]
    ) == UpdateStrategy(strategy=RollingUpdate(max_surge="25%", max_unavailable="25%"))

    assert parse_kube_strategy(
        [
            [
                json.dumps(
                    {
                        "strategy": {
                            "type_": "Recreate",
                        },
                    }
                )
            ]
        ]
    ) == UpdateStrategy(strategy=Recreate())

    assert parse_kube_strategy(
        [
            [
                json.dumps(
                    {
                        "strategy": {
                            "type_": "OnDelete",
                        },
                    }
                )
            ]
        ]
    ) == UpdateStrategy(strategy=OnDelete())

    assert parse_kube_strategy(
        [
            [
                json.dumps(
                    {
                        "strategy": {
                            "type_": "StatefulSetRollingUpdate",
                            "partition": 0,
                        },
                    }
                )
            ]
        ]
    ) == UpdateStrategy(strategy=StatefulSetRollingUpdate(partition=0))


def test_discover_kube_replicas() -> None:
    replicas = DeploymentReplicas(
        available=3,
        desired=3,
        updated=0,
        ready=3,
    )
    strategy = UpdateStrategy(
        strategy=RollingUpdate(
            max_surge="25%",
            max_unavailable="25%",
        )
    )
    assert list(discover_kube_replicas(replicas, strategy, None)) == [Service()]
    assert list(discover_kube_replicas(replicas, None, None)) == [Service()]
    assert not list(discover_kube_replicas(None, strategy, None))
    assert not list(discover_kube_replicas(None, None, None))


@pytest.mark.usefixtures("initialised_item_state")
def test_check_kube_replicas() -> None:
    assert list(
        check_kube_replicas(
            {},
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=3,
                ready=3,
            ),
            None,
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
    "params,replicas,strategy,value_store,expected_check_result",
    [
        pytest.param(
            {"update_duration": "no_levels"},
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=0,
                ready=3,
            ),
            UpdateStrategy(
                strategy=RollingUpdate(
                    max_surge="25%",
                    max_unavailable="25%",
                ),
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
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=0,
                ready=3,
            ),
            UpdateStrategy(
                strategy=RollingUpdate(
                    max_surge="25%",
                    max_unavailable="25%",
                ),
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
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=0,
                ready=3,
            ),
            UpdateStrategy(
                strategy=RollingUpdate(
                    max_surge="25%",
                    max_unavailable="25%",
                ),
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
    params: Mapping[str, VSResultAge],
    replicas: Replicas,
    strategy: UpdateStrategy,
    value_store: MutableMapping[str, Any],
    expected_check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(
            _check_kube_replicas(
                params, replicas, strategy, None, now=800.0, value_store=value_store
            )
        )
        == expected_check_result
    )


@pytest.mark.parametrize(
    "params,replicas,value_store,expected_check_result",
    [
        pytest.param(
            {"misscheduled_duration": "no_levels"},
            DaemonSetReplicas(
                available=3,
                desired=3,
                updated=3,
                ready=3,
                misscheduled=1,
            ),
            {"misscheduled_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 3/3"),
                Result(state=State.OK, summary="Up-to-date: 3/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 3.0, boundaries=(0.0, 3.0)),
                Result(state=State.OK, summary="Misscheduled: 1"),
                Metric("kube_misscheduled_replicas", 1.0),
                Result(state=State.OK, summary="Misscheduled for: 11 minutes 40 seconds"),
            ],
            id="Misscheduled is OK when no parameters are specified",
        ),
        pytest.param(
            {"misscheduled_duration": ("levels", (900, 1000))},
            DaemonSetReplicas(
                available=3,
                desired=3,
                updated=3,
                ready=3,
                misscheduled=1,
            ),
            {"misscheduled_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 3/3"),
                Result(state=State.OK, summary="Up-to-date: 3/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 3.0, boundaries=(0.0, 3.0)),
                Result(state=State.OK, summary="Misscheduled: 1"),
                Metric("kube_misscheduled_replicas", 1.0),
                Result(state=State.OK, summary="Misscheduled for: 11 minutes 40 seconds"),
            ],
            id="Misscheduled is OK when thresholds are not reached",
        ),
        pytest.param(
            {"misscheduled_duration": ("levels", (300, 500))},
            DaemonSetReplicas(
                available=3,
                desired=3,
                updated=3,
                ready=3,
                misscheduled=1,
            ),
            {"misscheduled_timestamp": 100.0},
            [
                Result(state=State.OK, summary="Ready: 3/3"),
                Result(state=State.OK, summary="Up-to-date: 3/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 3.0, boundaries=(0.0, 3.0)),
                Result(state=State.OK, summary="Misscheduled: 1"),
                Metric("kube_misscheduled_replicas", 1.0),
                Result(
                    state=State.CRIT,
                    summary="Misscheduled for: 11 minutes 40 seconds (warn/crit at 5 minutes 0 seconds/8 minutes 20 seconds)",
                ),
            ],
            id="Misscheduled thresholds are applied",
        ),
    ],
)
def test_check_kube_replicas_misscheduled_pods(
    params: Mapping[str, VSResultAge],
    replicas: DaemonSetReplicas,
    value_store: MutableMapping[str, Any],
    expected_check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(_check_kube_replicas(params, replicas, None, None, now=800.0, value_store=value_store))
        == expected_check_result
    )


@pytest.mark.parametrize(
    "params,replicas,value_store,expected_check_result",
    [
        pytest.param(
            {"not_ready_duration": "no_levels"},
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=3,
                ready=0,
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
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=3,
                ready=0,
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
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=3,
                ready=0,
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
    params: Mapping[str, VSResultAge],
    replicas: Replicas,
    value_store: MutableMapping[str, Any],
    expected_check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(_check_kube_replicas(params, replicas, None, None, now=800.0, value_store=value_store))
        == expected_check_result
    )


@pytest.mark.parametrize(
    "params,replicas,strategy,value_store,expected_check_result",
    [
        pytest.param(
            {
                "not_ready_duration": ("levels", (300, 500)),
                "update_duration": ("levels", (300, 500)),
            },
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=0,
                ready=0,
            ),
            UpdateStrategy(
                strategy=RollingUpdate(
                    max_surge="25%",
                    max_unavailable="25%",
                ),
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
            id="Not ready and outdated replicas are both checked and shown, strategy is RollingUpdate",
        ),
        pytest.param(
            {
                "not_ready_duration": ("levels", (300, 500)),
                "update_duration": ("levels", (300, 500)),
            },
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=0,
                ready=0,
            ),
            UpdateStrategy(strategy=Recreate()),
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
                    summary="Strategy: Recreate",
                ),
            ],
            id="Not ready and outdated replicas are both checked and shown, strategy is Recreate",
        ),
    ],
)
def test_check_kube_replicas_not_ready_and_outdated(
    params: Mapping[str, VSResultAge],
    replicas: Replicas,
    strategy: UpdateStrategy,
    value_store: MutableMapping[str, Any],
    expected_check_result: Sequence[Result | Metric],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mock_value_store():
        return value_store

    def mock_time():
        return 800.0

    monkeypatch.setattr(kube_replicas, "get_value_store", mock_value_store)
    monkeypatch.setattr(time, "time", mock_time)

    assert list(check_kube_replicas(params, replicas, strategy, None)) == expected_check_result


@pytest.mark.parametrize(
    "params,replicas,value_store,expected_check_result",
    [
        pytest.param(
            {
                "not_ready_duration": ("levels", (300, 500)),
                "update_duration": ("levels", (300, 500)),
            },
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=0,
                ready=3,
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
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=3,
                ready=0,
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
        pytest.param(
            {},
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=3,
                ready=0,
            ),
            {"not_ready_started_timestamp": None, "update_started_timestamp": None},
            [
                Result(state=State.OK, summary="Ready: 0/3"),
                Result(state=State.OK, summary="Up-to-date: 3/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 0.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 3.0, boundaries=(0.0, 3.0)),
                Result(state=State.OK, summary="Not ready for: 0 seconds"),
            ],
            id="Counter is started once the deployment has transitioned from a "
            "previously ready to a not ready replica state. Note that in this "
            "case, the value store is pre-populated with 'None'.",
        ),
        pytest.param(
            {},
            DeploymentReplicas(
                available=3,
                desired=3,
                updated=0,
                ready=3,
            ),
            {"not_ready_started_timestamp": None, "update_started_timestamp": None},
            [
                Result(state=State.OK, summary="Ready: 3/3"),
                Result(state=State.OK, summary="Up-to-date: 0/3"),
                Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_ready_replicas", 3.0, boundaries=(0.0, 3.0)),
                Metric("kube_updated_replicas", 0.0, boundaries=(0.0, 3.0)),
                Result(state=State.OK, summary="Not updated for: 0 seconds"),
            ],
            id="Counter is started once the deployment has transitioned from a "
            "previously updated to a not updated replica state. Note that in this "
            "case, the value store is pre-populated with 'None'.",
        ),
    ],
)
def test_check_kube_replicas_value_store_reset(
    params: Mapping[str, VSResultAge],
    replicas: Replicas,
    value_store: MutableMapping[str, Any],
    expected_check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(_check_kube_replicas(params, replicas, None, None, now=800.0, value_store=value_store))
        == expected_check_result
    )


def test_check_kube_replicas_statefulset_available() -> None:
    result = list(
        _check_kube_replicas(
            {},
            StatefulSetReplicas(desired=3, updated=0, ready=3, available=3),
            None,
            ControllerSpec(min_ready_seconds=10),
            now=800.0,
            value_store={"not_ready_started_timestamp": None, "update_started_timestamp": None},
        )
    )

    assert [r for r in result if isinstance(r, Result)] == [
        Result(state=State.OK, summary="Available: 3/3"),
        Result(state=State.OK, summary="Ready: 3/3"),
        Result(state=State.OK, summary="Up-to-date: 0/3"),
        Result(state=State.OK, summary="Not updated for: 0 seconds"),
    ]
    assert [r for r in result if isinstance(r, Metric)] == [
        Metric("kube_available_replicas", 3.0, boundaries=(0.0, 3.0)),
        Metric("kube_desired_replicas", 3.0, boundaries=(0.0, 3.0)),
        Metric("kube_ready_replicas", 3.0, boundaries=(0.0, 3.0)),
        Metric("kube_updated_replicas", 0.0, boundaries=(0.0, 3.0)),
    ]


def test_check_kube_replicas_statefuset_available_with_params() -> None:
    result = list(
        _check_kube_replicas(
            {"not_available_duration": ("levels", (300, 500))},
            StatefulSetReplicas(desired=3, updated=0, ready=3, available=2),
            None,
            ControllerSpec(min_ready_seconds=10),
            now=800.0,
            value_store={"not_available_started_timestamp": 100.0},
        )
    )
    not_available_results = [
        r for r in result if isinstance(r, Result) and r.summary.startswith("Not available for")
    ]
    assert [r.state for r in not_available_results] == [State.CRIT]
