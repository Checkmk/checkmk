#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import itertools
from typing import MutableMapping, Sequence, Tuple

import pytest

from cmk.base.plugins.agent_based import kube_pod_resources
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.kube_pod_resources import (
    _POD_RESOURCES_FIELDS,
    check_free_pods,
    check_kube_pod_resources,
    Params,
    PodPhaseTimes,
    VSResultPercent,
)
from cmk.base.plugins.agent_based.utils.kube import AllocatablePods, PodResources, PodSequence


@pytest.fixture(name="get_value_store")
def fixture_get_value_store(mocker):
    value_store: MutableMapping[str, PodPhaseTimes] = {}
    get_value_store_mock = mocker.MagicMock(return_value=value_store)
    mocker.patch.object(kube_pod_resources, "get_value_store", get_value_store_mock)
    return get_value_store_mock


@pytest.fixture(name="time_time")
def fixture_time(mocker):
    mocked_time = mocker.Mock()
    mocked_time.time = mocker.Mock(side_effect=itertools.count(0.1, 60.1))
    mocker.patch.object(kube_pod_resources, "time", mocked_time)
    return mocked_time


@pytest.mark.parametrize(
    "pending_pods_in_each_check_call, expected_result_in_each_check_call",
    [
        pytest.param(
            (
                ["pod"],
                ["pod"],
                ["pod"],
            ),
            (
                Result(state=State.OK, summary="Pending: 1"),
                Result(
                    state=State.WARN,
                    summary="Pending: 1, thereof 1 (pod) for longer than 1 minute 0 seconds",
                ),
                Result(
                    state=State.CRIT,
                    summary="Pending: 1, thereof 1 (pod) for longer than 2 minutes 0 seconds",
                ),
            ),
            id="crit",
        ),
        pytest.param(
            (
                ["pod_1", "pod_2", "pod_3", "pod_4"],
                ["pod_1", "pod_2", "pod_3", "pod_4"],
                ["pod_1", "pod_2", "pod_3", "pod_4"],
            ),
            (
                Result(state=State.OK, summary="Pending: 4"),
                Result(
                    state=State.WARN,
                    summary="Pending: 4, thereof 4 (pod_1, pod_2, pod_3, ...) for longer than 1 minute 0 seconds",
                ),
                Result(
                    state=State.CRIT,
                    summary="Pending: 4, thereof 4 (pod_1, pod_2, pod_3, ...) for longer than 2 minutes 0 seconds",
                ),
            ),
            id="crit_more_pods",
        ),
        pytest.param(
            (
                [],
                [],
                [],
            ),
            (
                Result(state=State.OK, summary="Pending: 0"),
                Result(state=State.OK, summary="Pending: 0"),
                Result(state=State.OK, summary="Pending: 0"),
            ),
            id="never_pending",
        ),
        pytest.param(
            (
                ["pod_1"],
                ["pod_2"],
                ["pod_3"],
            ),
            (
                Result(state=State.OK, summary="Pending: 1"),
                Result(state=State.OK, summary="Pending: 1"),
                Result(state=State.OK, summary="Pending: 1"),
            ),
            id="different_pods_pending",
        ),
        pytest.param(
            (
                ["pod"],
                ["pod"],
                [],
            ),
            (
                Result(state=State.OK, summary="Pending: 1"),
                Result(
                    state=State.WARN,
                    summary="Pending: 1, thereof 1 (pod) for longer than 1 minute 0 seconds",
                ),
                Result(state=State.OK, summary="Pending: 0"),
            ),
            id="resolved_pending",
        ),
        pytest.param(
            (
                ["pod_z"],
                ["pod_z", "pod_2"],
                ["pod_z", "pod_2", "pod_3"],
                ["pod_z", "pod_2", "pod_3"],
                ["pod_2", "pod_z", "pod_3"],  # let us put these pods in some random order
            ),
            (
                Result(state=State.OK, summary="Pending: 1"),
                Result(
                    state=State.WARN,
                    summary="Pending: 2, thereof 1 (pod_z) for longer than 1 minute 0 seconds",
                ),
                Result(
                    state=State.CRIT,
                    summary="Pending: 3, thereof 1 (pod_z) for longer than 2 minutes 0 seconds",
                ),
                Result(
                    state=State.CRIT,
                    summary="Pending: 3, thereof 2 (pod_z, pod_2) for longer than 2 minutes 0 seconds",
                ),
                Result(
                    state=State.CRIT,
                    summary="Pending: 3, thereof 3 (pod_z, pod_2, pod_3) for longer than 2 minutes 0 seconds",
                ),
            ),
            id="Are the pods ordered by duration they are pending?",
        ),
    ],
)
def test_check_phase_duration_with_different_pods(
    pending_pods_in_each_check_call: Tuple[PodSequence, ...],
    expected_result_in_each_check_call: Tuple[Result, ...],
    time_time,
    get_value_store,
) -> None:
    """
    We simulate multiple calls to check function at different points in time.
    expected_result_in_each_check_call corresponds to the Results returned at different points in
    time, which are relevant to the behaviour of pending pods, i.e., check_kube_pod_resources will
    return other Results/Metrics, but will only return one Result, which is related to pending.

    Here we focus on different sequences of pending pods.
    """
    params = Params(pending=("levels", (60, 120)), free="no_levels")
    for pending_pods, expected_result in zip(
        pending_pods_in_each_check_call,
        expected_result_in_each_check_call,
        # strict=True, would be nice
    ):
        assert (
            tuple(check_kube_pod_resources(params, PodResources(pending=pending_pods), None))[2]
            == expected_result
        )


@pytest.mark.parametrize(
    "params_in_each_check_call, expected_result_in_each_check_call",
    [
        pytest.param(
            # If the user deactivates a rule and then later activates it again, the phase duration
            # should be persistent.
            (
                Params(pending=("levels", (60, 120)), free="no_levels"),
                Params(pending="no_levels", free="no_levels"),
                Params(pending=("levels", (60, 120)), free="no_levels"),
            ),
            (
                Result(state=State.OK, summary="Pending: 1"),
                Result(state=State.OK, summary="Pending: 1"),
                Result(
                    state=State.CRIT,
                    summary="Pending: 1, thereof 1 (pod) for longer than 2 minutes 0 seconds",
                ),
            ),
            id="deactivate_levels_and_turn_on_again",
        ),
        pytest.param(
            (
                Params(pending="no_levels", free="no_levels"),
                Params(pending="no_levels", free="no_levels"),
                Params(pending="no_levels", free="no_levels"),
            ),
            (
                Result(state=State.OK, summary="Pending: 1"),
                Result(state=State.OK, summary="Pending: 1"),
                Result(state=State.OK, summary="Pending: 1"),
            ),
            id="ok_because_no_levels",
        ),
    ],
)
def test_check_phase_duration_with_changing_params(
    params_in_each_check_call: Tuple[Params, ...],
    expected_result_in_each_check_call: Tuple[Result, ...],
    time_time,
    get_value_store,
) -> None:
    """
    We simulate multiple calls to check function at different points in time.
    expected_result_in_each_check_call corresponds to the Results returned at different points in
    time, which are relevant to the behaviour of pending pods, i.e., check_kube_pod_resources will
    return other Results/Metrics, but will only return one Result, which is related to pending.

    Here we focus on activating/deactivating rules.
    """
    for params, expected_result in zip(
        params_in_each_check_call,
        expected_result_in_each_check_call,
        # strict=True, would be nice
    ):
        assert (
            tuple(check_kube_pod_resources(params, PodResources(pending=["pod"]), None))[2]
            == expected_result
        )


@pytest.mark.parametrize(
    "pending_pods_in_each_check_call,expected_result_in_each_check_call",
    [
        pytest.param(
            (
                ["pod_1"],
                ["pod_2"],
                ["pod_3"],
                ["pod_4"],
            ),
            (
                Result(state=State.OK, summary="Unknown: 1", details="Unknown: 1 (pod_1)"),
                Result(state=State.OK, summary="Unknown: 1", details="Unknown: 1 (pod_2)"),
                Result(state=State.OK, summary="Unknown: 1", details="Unknown: 1 (pod_3)"),
                Result(state=State.OK, summary="Unknown: 1", details="Unknown: 1 (pod_4)"),
            ),
            id="different_pods_unknown",
        ),
        pytest.param(
            (
                [],
                [],
                [],
                [],
            ),
            (
                Result(state=State.OK, summary="Unknown: 0", details="Unknown: 0"),
                Result(state=State.OK, summary="Unknown: 0", details="Unknown: 0"),
                Result(state=State.OK, summary="Unknown: 0", details="Unknown: 0"),
                Result(state=State.OK, summary="Unknown: 0", details="Unknown: 0"),
            ),
            id="no_unknown_pods",
        ),
    ],
)
def test_check_bevaviour_if_there_are_unknown_pods(
    pending_pods_in_each_check_call: Tuple[PodSequence, ...],
    expected_result_in_each_check_call: Tuple[Result, ...],
    time_time,
    get_value_store,
) -> None:
    """
    We simulate multiple calls to check function at different points in time.
    expected_result_in_each_check_call corresponds to the Results returned at different points in
    time, which are relevant to the behaviour of unknown pods, i.e., check_kube_pod_resources will
    return other Results/Metrics, but will only return one Result, which is related to unknown.
    """
    for pending_pods, expected_result in zip(
        pending_pods_in_each_check_call,
        expected_result_in_each_check_call,
        # strict=True, would be nice
    ):
        assert (
            tuple(
                check_kube_pod_resources(
                    Params(pending="no_levels", free="no_levels"),
                    PodResources(unknown=pending_pods),
                    None,
                )
            )[8]
            == expected_result
        )


@pytest.mark.parametrize(
    "pending_pods_in_each_check_call,param,expected_result_in_each_check_call",
    [
        pytest.param(
            (
                [],
                ["pod_1"],
                ["pod_1", "pod_2"],
                ["pod_1", "pod_2", "pod_3"],
            ),
            "no_levels",
            [
                Result(state=State.OK, notice="Free: 2"),
                Result(state=State.OK, notice="Free: 1"),
                Result(state=State.OK, notice="Free: 0"),
                Result(state=State.OK, notice="Free: 0"),
            ],
            id="Total number of free pods decreases to zero with levels disabled.",
        ),
        pytest.param(
            (
                [],
                ["pod_1"],
                ["pod_1", "pod_2"],
                ["pod_1", "pod_2", "pod_3"],
            ),
            ("levels_abs", (2, 1)),
            [
                Result(state=State.OK, notice="Free: 2"),
                Result(state=State.WARN, notice="Free: 1 (warn/crit below 2/1)"),
                Result(state=State.CRIT, notice="Free: 0 (warn/crit below 2/1)"),
                Result(state=State.CRIT, notice="Free: 0 (warn/crit below 2/1)"),
            ],
            id="Total number of free pods decreases to zero with absolute levels set.",
        ),
        pytest.param(
            (
                [],
                ["pod_1"],
                ["pod_1", "pod_2"],
                ["pod_1", "pod_2", "pod_3"],
            ),
            ("levels_free", (100.0, 50.0)),
            [
                Result(state=State.OK, notice="Free: 2"),
                Result(state=State.WARN, notice="Free: 1 (warn/crit below 2/1)"),
                Result(state=State.CRIT, notice="Free: 0 (warn/crit below 2/1)"),
                Result(state=State.CRIT, notice="Free: 0 (warn/crit below 2/1)"),
            ],
            id="Total number of free pods decreases to zero with percentual levels set.",
        ),
    ],
)
def test_check_levels_free_pods(
    pending_pods_in_each_check_call: Tuple[PodSequence, ...],
    param: VSResultPercent,
    expected_result_in_each_check_call: Sequence[Result],
) -> None:
    for pending_pods, expected_result in zip(
        pending_pods_in_each_check_call,
        expected_result_in_each_check_call,
    ):
        result, _ = check_free_pods(
            param,
            PodResources(pending=pending_pods),
            allocatable_pods=2,
        )
        assert result == expected_result


@pytest.mark.parametrize(
    "param, expected_result",
    [
        pytest.param(
            ("levels_free", (50.1, 50.0)),
            Result(state=State.WARN, notice="Free: 1 (warn/crit below 2/1)"),
            id="The number of allocatable pods is two, and therefore the number of free pods is "
            "below 50.1 if and only if it is below 2.",
        ),
        pytest.param(
            ("levels_free", (100.0, 50.0)),
            Result(state=State.WARN, notice="Free: 1 (warn/crit below 2/1)"),
            id="The number of allocatable pods is two, and therefore the number of free pods is "
            "below 100.0 if and only if it is below 2.",
        ),
    ],
)
def test_check_matches_what_valuespec_promises(
    param: VSResultPercent, expected_result: Sequence[Result]
) -> None:
    """The rule set for free pods looks like this:
    Warning below x %
    Crit below y %
    These percentual values need to be converted to absolute levels such that, what the rule set
    promises, is true.
    """
    result, _ = check_free_pods(
        param,
        PodResources(pending=["pod_1"]),
        allocatable_pods=2,
    )
    assert result == expected_result


_PYTEST_PARAMS_OVER_ALL_LOOK = [
    pytest.param(
        (
            ["pod"],
            ["pod"],
            ["pod"],
        ),
        (
            Params(pending=("levels", (60, 120)), free="no_levels"),
            Params(pending=("levels", (60, 120)), free="no_levels"),
            Params(pending=("levels", (60, 120)), free="no_levels"),
        ),
        (
            Result(state=State.OK, summary="Running: 0"),
            Metric("kube_pod_running", 0.0),
            Result(
                state=State.CRIT,
                summary="Pending: 1, thereof 1 (pod) for longer than 2 minutes 0 seconds",
            ),
            Metric("kube_pod_pending", 1.0),
            Result(state=State.OK, summary="Succeeded: 0"),
            Metric("kube_pod_succeeded", 0.0),
            Result(state=State.OK, summary="Failed: 0"),
            Metric("kube_pod_failed", 0.0),
            Result(state=State.OK, summary="Unknown: 0"),
            # Results/Metrics below only for check_kube_pod_resources_with_capacity
            Result(state=State.OK, summary="Allocatable: 110"),
            Result(state=State.OK, notice="Capacity: 110"),
            Result(state=State.OK, notice="Free: 109"),
            Metric("kube_pod_free", 109.0),
            Metric("kube_pod_allocatable", 110.0),
        ),
        id="crit",
    ),
    pytest.param(
        (["pod_1"],),
        (Params(pending=("levels", (60, 120)), free="no_levels"),),
        (
            Result(state=State.OK, summary="Running: 0"),
            Metric("kube_pod_running", 0.0),
            Result(state=State.OK, summary="Pending: 1"),
            Metric("kube_pod_pending", 1.0),
            Result(state=State.OK, summary="Succeeded: 0"),
            Metric("kube_pod_succeeded", 0.0),
            Result(state=State.OK, summary="Failed: 0"),
            Metric("kube_pod_failed", 0.0),
            Result(state=State.OK, summary="Unknown: 0"),
            # Results/Metrics below only for check_kube_pod_resources_with_capacity
            Result(state=State.OK, summary="Allocatable: 110"),
            Result(state=State.OK, notice="Capacity: 110"),
            Result(state=State.OK, notice="Free: 109"),
            Metric("kube_pod_free", 109.0),
            Metric("kube_pod_allocatable", 110.0),
        ),
        id="ok",
    ),
]


@pytest.mark.parametrize(
    "pending_pods_in_each_check_call,params_in_each_check_call,expected_result",
    _PYTEST_PARAMS_OVER_ALL_LOOK,
)
def test_check_kube_pod_resources_overall_look(
    pending_pods_in_each_check_call: Tuple[PodSequence, ...],
    params_in_each_check_call: Tuple[Params, ...],
    expected_result,
    time_time,
    get_value_store,
) -> None:
    for pod_names, params in zip(pending_pods_in_each_check_call, params_in_each_check_call):
        result = tuple(
            check_kube_pod_resources(
                params=params,
                section_kube_pod_resources=PodResources(pending=pod_names),
                section_kube_allocatable_pods=None,
            )
        )
    assert result == expected_result[:9]


@pytest.mark.parametrize(
    "pending_pods_in_each_check_call,params_in_each_check_call,expected_result",
    _PYTEST_PARAMS_OVER_ALL_LOOK,
)
def test_check_kube_pod_resources_with_capacity_overall_look(
    pending_pods_in_each_check_call: Tuple[PodSequence, ...],
    params_in_each_check_call: Tuple[Params, ...],
    expected_result,
    time_time,
    get_value_store,
) -> None:
    for pod_names, params in zip(pending_pods_in_each_check_call, params_in_each_check_call):
        result = tuple(
            check_kube_pod_resources(
                params=params,
                section_kube_pod_resources=PodResources(pending=pod_names),
                section_kube_allocatable_pods=AllocatablePods(allocatable=110, capacity=110),
            )
        )
    assert result == expected_result


def test_pod_resource_fields() -> None:
    """
    _POD_RESOURCES_FIELDS is used, if do not have an instance of type PodResources. Instead, we
    could use the method below, but we don't want to rely on it's behaviour.
    """
    assert _POD_RESOURCES_FIELDS == tuple(PodResources.__fields__)
