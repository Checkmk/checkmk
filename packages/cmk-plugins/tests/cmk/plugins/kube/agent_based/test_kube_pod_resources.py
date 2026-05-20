#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import itertools
from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.kube.agent_based.kube_pod_resources import (
    _check_kube_pod_resources,
    _POD_RESOURCES_FIELDS,
    check_free_pods,
    Params,
    PodPhaseCountLevels,
    ValueStore,
    VSResultPercent,
)
from cmk.plugins.kube.schemata.section import AllocatablePods, PodResources, PodSequence


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
    pending_pods_in_each_check_call: tuple[PodSequence, ...],
    expected_result_in_each_check_call: tuple[Result, ...],
) -> None:
    """
    We simulate multiple calls to check function at different points in time.
    expected_result_in_each_check_call corresponds to the Results returned at different points in
    time, which are relevant to the behaviour of pending pods, i.e., check_kube_pod_resources will
    return other Results/Metrics, but will only return one Result, which is related to pending.

    Here we focus on different sequences of pending pods.
    """
    params = Params(pending=("levels", (60, 120)), free="no_levels")
    value_store: ValueStore = {}
    for time, pending_pods, expected_result in zip(
        itertools.count(0.1, 60.1),
        pending_pods_in_each_check_call,
        expected_result_in_each_check_call,
        # strict=True, would be nice
    ):
        assert (
            tuple(
                _check_kube_pod_resources(
                    time, value_store, params, PodResources(pending=pending_pods), None
                )
            )[2]
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
    params_in_each_check_call: tuple[Params, ...],
    expected_result_in_each_check_call: tuple[Result, ...],
) -> None:
    """
    We simulate multiple calls to check function at different points in time.
    expected_result_in_each_check_call corresponds to the Results returned at different points in
    time, which are relevant to the behaviour of pending pods, i.e., check_kube_pod_resources will
    return other Results/Metrics, but will only return one Result, which is related to pending.

    Here we focus on activating/deactivating rules.
    """
    value_store: ValueStore = {}
    for time, params, expected_result in zip(
        itertools.count(0.1, 60.1),
        params_in_each_check_call,
        expected_result_in_each_check_call,
        # strict=True, would be nice
    ):
        assert (
            tuple(
                _check_kube_pod_resources(
                    time, value_store, params, PodResources(pending=["pod"]), None
                )
            )[2]
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
    pending_pods_in_each_check_call: tuple[PodSequence, ...],
    expected_result_in_each_check_call: tuple[Result, ...],
) -> None:
    """
    We simulate multiple calls to check function at different points in time.
    expected_result_in_each_check_call corresponds to the Results returned at different points in
    time, which are relevant to the behaviour of unknown pods, i.e., check_kube_pod_resources will
    return other Results/Metrics, but will only return one Result, which is related to unknown.
    """
    value_store: ValueStore = {}
    for time, pending_pods, expected_result in zip(
        itertools.count(0.1, 60.1),
        pending_pods_in_each_check_call,
        expected_result_in_each_check_call,
        # strict=True, would be nice
    ):
        assert (
            tuple(
                _check_kube_pod_resources(
                    time,
                    value_store,
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
    pending_pods_in_each_check_call: tuple[PodSequence, ...],
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
    pending_pods_in_each_check_call: tuple[PodSequence, ...],
    params_in_each_check_call: tuple[Params, ...],
    expected_result: Sequence[Result | Metric],
) -> None:
    value_store: ValueStore = {}
    result: CheckResult = tuple()
    for time, pod_names, params in zip(
        itertools.count(0.1, 60.1), pending_pods_in_each_check_call, params_in_each_check_call
    ):
        result = tuple(
            _check_kube_pod_resources(
                time,
                value_store,
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
    pending_pods_in_each_check_call: tuple[PodSequence, ...],
    params_in_each_check_call: tuple[Params, ...],
    expected_result: Sequence[Result | Metric],
) -> None:
    value_store: ValueStore = {}
    result: CheckResult = tuple()
    for time, pod_names, params in zip(
        itertools.count(0.1, 60.1), pending_pods_in_each_check_call, params_in_each_check_call
    ):
        result = tuple(
            _check_kube_pod_resources(
                time,
                value_store,
                params=params,
                section_kube_pod_resources=PodResources(pending=pod_names),
                section_kube_allocatable_pods=AllocatablePods(allocatable=110, capacity=110),
            )
        )
    assert result == expected_result


def test_pending_count_levels_absent_yields_no_extra_result() -> None:
    result = tuple(
        _check_kube_pod_resources(
            0.1,
            {},
            Params(pending="no_levels", free="no_levels"),
            PodResources(pending=["p1", "p2"]),
            None,
        )
    )
    # Without pod_phase_count_levels we keep the original layout: 5 phase results + 4 metrics.
    assert len(result) == 9


@pytest.mark.parametrize(
    "pod_count,count_levels,pending_seconds,duration_param,expected_state,expected_summary",
    [
        pytest.param(
            2,
            (10, 20),
            30,
            ("levels", (60, 120)),
            State.OK,
            "Pending: 2",
            id="neither_trips",
        ),
        pytest.param(
            15,
            (10, 20),
            30,
            ("levels", (60, 120)),
            State.WARN,
            "Pending: 15 (warn/crit at 10/20)",
            id="count_warn_only",
        ),
        pytest.param(
            25,
            (10, 20),
            30,
            ("levels", (60, 120)),
            State.CRIT,
            "Pending: 25 (warn/crit at 10/20)",
            id="count_crit_only",
        ),
        pytest.param(
            2,
            (10, 20),
            90,
            ("levels", (60, 120)),
            State.WARN,
            "Pending: 2, thereof 2 (pod-0, pod-1) for longer than 1 minute 0 seconds",
            id="duration_warn_only",
        ),
        pytest.param(
            2,
            (10, 20),
            200,
            ("levels", (60, 120)),
            State.CRIT,
            "Pending: 2, thereof 2 (pod-0, pod-1) for longer than 2 minutes 0 seconds",
            id="duration_crit_only",
        ),
        pytest.param(
            15,
            (10, 20),
            90,
            ("levels", (60, 120)),
            State.WARN,
            "Pending: 15 (warn/crit at 10/20), thereof 15 (pod-0, pod-1, pod-2, ...) for longer than 1 minute 0 seconds",
            id="both_warn",
        ),
        pytest.param(
            15,
            (10, 20),
            200,
            ("levels", (60, 120)),
            State.CRIT,
            "Pending: 15 (warn/crit at 10/20), thereof 15 (pod-0, pod-1, pod-2, ...) for longer than 2 minutes 0 seconds",
            id="count_warn_duration_crit",
        ),
        pytest.param(
            25,
            (10, 20),
            90,
            ("levels", (60, 120)),
            State.CRIT,
            "Pending: 25 (warn/crit at 10/20), thereof 25 (pod-0, pod-1, pod-2, ...) for longer than 1 minute 0 seconds",
            id="count_crit_duration_warn",
        ),
        pytest.param(
            25,
            (10, 20),
            200,
            ("levels", (60, 120)),
            State.CRIT,
            "Pending: 25 (warn/crit at 10/20), thereof 25 (pod-0, pod-1, pod-2, ...) for longer than 2 minutes 0 seconds",
            id="both_crit",
        ),
        pytest.param(
            2,
            (10, 20),
            30,
            "no_levels",
            State.OK,
            "Pending: 2",
            id="count_below_warn_duration_disabled",
        ),
        pytest.param(
            15,
            (10, 20),
            30,
            "no_levels",
            State.WARN,
            "Pending: 15 (warn/crit at 10/20)",
            id="count_warn_duration_disabled",
        ),
        pytest.param(
            25,
            (10, 20),
            30,
            "no_levels",
            State.CRIT,
            "Pending: 25 (warn/crit at 10/20)",
            id="count_crit_duration_disabled",
        ),
    ],
)
def test_pending_count_and_duration_interaction(
    pod_count: int,
    count_levels: tuple[int, int],
    pending_seconds: float,
    duration_param: object,
    expected_state: State,
    expected_summary: str,
) -> None:
    """
    Verify the merged Pending Result when count-based and time-based level rules both apply.
    Structured so that adding analogous coverage for other phases later (e.g. Failed) only
    requires swapping the section field and result index.
    """
    pods = [f"pod-{i}" for i in range(pod_count)]
    now = 1000.0
    value_store: ValueStore = {"pending": {pod: now - pending_seconds for pod in pods}}
    result = tuple(
        _check_kube_pod_resources(
            now,
            value_store,
            Params(
                pending=duration_param,  # type: ignore[typeddict-item]
                free="no_levels",
                pod_phase_count_levels={"pending": count_levels},
            ),
            PodResources(pending=pods),
            None,
        )
    )
    pending_result = result[2]
    assert isinstance(pending_result, Result)
    assert pending_result.state == expected_state
    assert pending_result.summary == expected_summary
    assert len(result) == 9


@pytest.mark.parametrize(
    "pod_count,count_levels,expected_state,expected_summary",
    [
        pytest.param(
            2,
            (10, 20),
            State.OK,
            "Failed: 2",
            id="count_below_warn",
        ),
        pytest.param(
            15,
            (10, 20),
            State.WARN,
            "Failed: 15 (warn/crit at 10/20)",
            id="count_warn_only",
        ),
        pytest.param(
            25,
            (10, 20),
            State.CRIT,
            "Failed: 25 (warn/crit at 10/20)",
            id="count_crit_only",
        ),
        pytest.param(
            25,
            None,
            State.OK,
            "Failed: 25",
            id="no_levels",
        ),
    ],
)
def test_failed_count(
    pod_count: int,
    count_levels: tuple[int, int] | None,
    expected_state: State,
    expected_summary: str,
) -> None:
    pods = [f"pod-{i}" for i in range(pod_count)]
    now = 1000.0
    pod_phase_count_levels: PodPhaseCountLevels = {}
    if count_levels is not None:
        pod_phase_count_levels["failed"] = count_levels
    result = tuple(
        _check_kube_pod_resources(
            now,
            {},
            Params(
                pending="no_levels",
                free="no_levels",
                pod_phase_count_levels=pod_phase_count_levels,
            ),
            PodResources(failed=pods),
            None,
        )
    )
    failed_result = result[6]
    assert isinstance(failed_result, Result)
    assert failed_result.state == expected_state
    assert failed_result.summary == expected_summary
    assert len(result) == 9


def test_pod_resource_fields() -> None:
    """
    _POD_RESOURCES_FIELDS is used, if do not have an instance of type PodResources. Instead, we
    could use the method below, but we don't want to rely on it's behaviour.
    """
    assert _POD_RESOURCES_FIELDS == tuple(PodResources.__pydantic_fields__)
