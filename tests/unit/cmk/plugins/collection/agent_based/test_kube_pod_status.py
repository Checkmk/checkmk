#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from itertools import count

import pytest

from cmk.agent_based.v2 import CheckResult, Result, State
from cmk.plugins.collection.agent_based import kube_pod_status
from cmk.plugins.collection.agent_based.kube_pod_status import (
    _check_kube_pod_status,
    check_kube_pod_status,
    DEFAULT_PARAMS,
    ValueStore,
)
from cmk.plugins.kube.schemata.api import (
    ContainerRunningState,
    ContainerStateType,
    ContainerStatus,
    ContainerTerminatedState,
    ContainerWaitingState,
    Phase,
)
from cmk.plugins.kube.schemata.section import PodContainers, PodLifeCycle


def _mocked_container_info_from_state(
    state: ContainerRunningState | ContainerTerminatedState | ContainerWaitingState,
) -> ContainerStatus:
    # The check only requires the state field to be populated, therefore all the other fields are
    # filled with some arbitrary values.
    return ContainerStatus(
        container_id="some_id",
        image_id="some_other_id",
        name="some_name",
        image="some_image",
        ready=False,
        state=state,
        restart_count=0,
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "section_kube_pod_containers, section_kube_pod_lifecycle, expected_result",
    [
        pytest.param(
            PodContainers(
                containers={
                    "running": _mocked_container_info_from_state(
                        ContainerRunningState(
                            type=ContainerStateType.running, start_time=1639135964
                        )
                    ),
                },
            ),
            PodLifeCycle(phase=Phase.RUNNING),
            [Result(state=State.OK, summary="Running")],
            id="A single running container",
        ),
        pytest.param(
            PodContainers(
                containers={
                    "downloading-container": _mocked_container_info_from_state(
                        ContainerWaitingState(
                            type=ContainerStateType.waiting, reason="ContainerCreating", detail=None
                        )
                    )
                }
            ),
            PodLifeCycle(phase=Phase.PENDING),
            [
                Result(state=State.OK, summary="Pending: since 0 seconds"),
            ],
            id="Container image is still being downloaded.",
        ),
        pytest.param(
            PodContainers(
                containers={
                    "succeeding-container": _mocked_container_info_from_state(
                        ContainerTerminatedState(
                            type=ContainerStateType.terminated,
                            exit_code=0,
                            start_time=1639135989,
                            end_time=1639135989,
                            reason="Completed",
                            detail=None,
                        )
                    )
                }
            ),
            PodLifeCycle(phase=Phase.SUCCEEDED),
            [Result(state=State.OK, summary="Succeeded")],
            id="Container exits with 0, and is not restarted",
        ),
    ],
)
def test_check_kube_pod_status_no_issues_in_containers(
    section_kube_pod_containers: PodContainers | None,
    section_kube_pod_lifecycle: PodLifeCycle | None,
    expected_result: CheckResult,
) -> None:
    """
    Tested Pods have a single container which is configured correctly and in a good state.
    """
    assert (
        list(
            check_kube_pod_status(
                DEFAULT_PARAMS, section_kube_pod_containers, None, section_kube_pod_lifecycle
            )
        )
        == expected_result
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "section_kube_pod_containers, section_kube_pod_lifecycle, expected_result",
    [
        pytest.param(
            PodContainers(
                containers={
                    "failing-container": _mocked_container_info_from_state(
                        ContainerWaitingState(
                            type=ContainerStateType.waiting,
                            reason="CrashLoopBackOff",
                            detail="back-off 5m0s restarting failed container=busybox pod=container-exits-with-1-but-is-restarted_default(c654fe38-6551-473f-8cd1-4a9b06e609de)",
                        )
                    )
                }
            ),
            PodLifeCycle(phase=Phase.RUNNING),
            [
                Result(state=State.OK, summary="CrashLoopBackOff: since 0 seconds"),
                Result(
                    state=State.OK,
                    notice="some_name: back-off 5m0s restarting failed container=busybox pod=container-exits-with-1-but-is-restarted_default(c654fe38-6551-473f-8cd1-4a9b06e609de)",
                ),
            ],
            id="Container exits with 0 or 1 (exit code does not change container state), and is restarted",
        ),
        pytest.param(
            PodContainers(
                containers={
                    "failing-container": _mocked_container_info_from_state(
                        ContainerTerminatedState(
                            type=ContainerStateType.terminated,
                            exit_code=1,
                            start_time=1639136018,
                            end_time=1639136018,
                            reason="Error",
                            detail=None,
                        )
                    )
                },
            ),
            PodLifeCycle(phase=Phase.FAILED),
            [
                Result(state=State.OK, summary="Error: since 0 seconds"),
            ],
            id="Container exits with 1, and is not restarted",
        ),
    ],
)
def test_check_kube_pod_status_failing_container(
    section_kube_pod_containers: PodContainers | None,
    section_kube_pod_lifecycle: PodLifeCycle | None,
    expected_result: CheckResult,
) -> None:
    """
    Tested Pods with a single failing or misconfigured container.
    """
    assert (
        list(
            check_kube_pod_status(
                DEFAULT_PARAMS, section_kube_pod_containers, None, section_kube_pod_lifecycle
            )
        )
        == expected_result
    )


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "section_kube_pod_containers, section_kube_pod_lifecycle, expected_result",
    [
        pytest.param(
            PodContainers(
                containers={
                    "failing-container": _mocked_container_info_from_state(
                        ContainerTerminatedState(
                            type=ContainerStateType.terminated,
                            exit_code=1,
                            start_time=1639136911,
                            end_time=1639136911,
                            reason="Error",
                            detail=None,
                        )
                    ),
                    "running": _mocked_container_info_from_state(
                        ContainerTerminatedState(
                            type=ContainerStateType.terminated,
                            exit_code=0,
                            start_time=1639136913,
                            end_time=1639137513,
                            reason="Completed",
                            detail=None,
                        )
                    ),
                }
            ),
            PodLifeCycle(phase=Phase.FAILED),
            [
                Result(state=State.OK, summary="Error: since 0 seconds"),
            ],
            id="Both containers are terminating, one with exit code 1, the other with exit code 0.",
        ),
        pytest.param(
            PodContainers(
                containers={
                    "failing-container": _mocked_container_info_from_state(
                        state=ContainerWaitingState(
                            type=ContainerStateType.waiting,
                            reason="CrashLoopBackOff",
                            detail="back-off 5m0s restarting failed container=busybox pod=failingcontainer-imagepullbackerror_default(e7437bfb-3043-44a0-a071-4221ab43c550)",
                        )
                    ),
                    "wrong-image-name": _mocked_container_info_from_state(
                        state=ContainerWaitingState(
                            type=ContainerStateType.waiting,
                            reason="ImagePullBackOff",
                            detail='Back-off pulling image "busybox1"',
                        )
                    ),
                }
            ),
            PodLifeCycle(phase=Phase.PENDING),
            [
                Result(state=State.OK, summary="CrashLoopBackOff: since 0 seconds"),
                Result(
                    state=State.OK,
                    notice="some_name: back-off 5m0s restarting failed container=busybox pod=failingcontainer-imagepullbackerror_default(e7437bfb-3043-44a0-a071-4221ab43c550)",
                ),
                Result(state=State.OK, notice='some_name: Back-off pulling image "busybox1"'),
            ],
            id="One container has incorrect image name, one container fails with exit code 0",
        ),
        pytest.param(
            None,
            PodLifeCycle(phase=Phase.PENDING),
            [
                Result(state=State.OK, summary="Pending: since 0 seconds"),
            ],
            id="One container is too large to be scheduled, one container fails",
        ),
    ],
)
def test_check_kube_pod_status_multiple_issues(
    section_kube_pod_containers: PodContainers | None,
    section_kube_pod_lifecycle: PodLifeCycle | None,
    expected_result: CheckResult,
) -> None:
    """
    Tested Pods have two containers with different issues, which are then summarized into a
    single status.
    """
    assert (
        list(
            check_kube_pod_status(
                DEFAULT_PARAMS, section_kube_pod_containers, None, section_kube_pod_lifecycle
            )
        )
        == expected_result
    )


def test_check_alert_if_pending_too_long() -> None:
    value_store: ValueStore = {}
    section_kube_pod_containers = None
    section_kube_pod_lifecycle = PodLifeCycle(phase=Phase.PENDING)
    params = kube_pod_status.Params(
        groups=[
            (("levels", (60, 120)), ["Pending"]),
            ("no_levels", [".*"]),
        ]
    )

    expected_results = (
        (State.OK, "0 seconds"),
        (State.WARN, "1 minute 0 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)"),
        (State.CRIT, "2 minutes 0 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)"),
    )
    for time, expected_result in zip(count(0.1, 60.1), expected_results):
        expected_state, expected_message = expected_result
        summary_result, *_ = _check_kube_pod_status(
            time, value_store, params, section_kube_pod_containers, None, section_kube_pod_lifecycle
        )
        assert isinstance(summary_result, Result)
        assert summary_result.state == expected_state
        assert summary_result.summary.endswith(expected_message)


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "section_kube_pod_init_containers, section_kube_pod_containers, section_kube_pod_lifecycle, expected_result",
    [
        pytest.param(
            PodContainers(
                containers={
                    "failing-container": _mocked_container_info_from_state(
                        ContainerTerminatedState(
                            type=ContainerStateType.terminated,
                            exit_code=1,
                            start_time=1639136911,
                            end_time=1639136911,
                            reason="Error",
                            detail=None,
                        )
                    ),
                }
            ),
            PodContainers(
                containers={
                    "failing-container-2": _mocked_container_info_from_state(
                        state=ContainerWaitingState(reason="PodInitializing")
                    ),
                }
            ),
            PodLifeCycle(phase=Phase.PENDING),
            "Init:Error",
            id="Both containers have an error, but the second container is not intialized",
        ),
    ],
)
def test_check_kube_pod_status_init_container_broken(
    section_kube_pod_init_containers: PodContainers,
    section_kube_pod_containers: PodContainers,
    section_kube_pod_lifecycle: PodLifeCycle | None,
    expected_result: str,
) -> None:
    """
    Tested Pods has a failing init-container.
    """
    summary_result, *_ = check_kube_pod_status(
        DEFAULT_PARAMS,
        section_kube_pod_containers,
        section_kube_pod_init_containers,
        section_kube_pod_lifecycle,
    )
    assert isinstance(summary_result, Result)
    assert summary_result.summary.startswith(expected_result)


def test_check_alert_resets() -> None:
    value_store: ValueStore = {}
    params = kube_pod_status.Params(
        groups=[
            (("levels", (60, 120)), ["Pending"]),
            (("levels", (60, 120)), ["Running"]),
            ("no_levels", [".*"]),
        ]
    )
    section_kube_pod_containers = None

    pod_cycles = (
        PodLifeCycle(phase=Phase.PENDING),
        PodLifeCycle(phase=Phase.PENDING),
        PodLifeCycle(phase=Phase.RUNNING),
        PodLifeCycle(phase=Phase.PENDING),
    )

    expectations = (
        (
            State.OK,
            "0 seconds",
            None,
        ),
        (
            State.WARN,
            "1 minute 0 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
            None,
        ),
        (
            State.OK,
            "0 seconds",
            None,
        ),
        (
            State.OK,
            "0 seconds",
            None,
        ),
    )

    for time, expected, section_kube_pod_lifecycle in zip(
        count(0.1, 60.1), expectations, pod_cycles
    ):
        expected_state, expected_summary, expected_notice = expected
        summary_result, *notice = _check_kube_pod_status(
            time, value_store, params, section_kube_pod_containers, None, section_kube_pod_lifecycle
        )
        assert isinstance(summary_result, Result)
        assert summary_result.state == expected_state
        assert summary_result.summary.endswith(expected_summary)
        if expected_notice is None:
            assert [] == notice
        else:
            assert isinstance(notice[0], Result)
            assert expected_notice == notice[0].details


def test_check_group_timer() -> None:
    value_store: ValueStore = {}
    params = kube_pod_status.Params(
        groups=[
            (("levels", (60, 120)), ["Pending", "Running"]),
            ("no_levels", [".*"]),
        ]
    )
    section_kube_pod_containers = None

    pod_cycles = (
        PodLifeCycle(phase=Phase.PENDING),
        PodLifeCycle(phase=Phase.PENDING),
        PodLifeCycle(phase=Phase.RUNNING),
        PodLifeCycle(phase=Phase.PENDING),
    )

    expectations = (
        (
            State.OK,
            "0 seconds",
            None,
        ),
        (
            State.WARN,
            "1 minute 0 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
            None,
        ),
        (
            State.CRIT,
            "2 minutes 0 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
            "Seen: Pending (2 minutes 0 seconds), Running (0 seconds)",
        ),
        (
            State.CRIT,
            "3 minutes 0 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
            "Seen: Pending (2 minutes 0 seconds), Running (1 minute 0 seconds)",
        ),
    )

    for time, expected, section_kube_pod_lifecycle in zip(
        count(0.1, 60.1), expectations, pod_cycles
    ):
        expected_state, expected_summary, expected_notice = expected
        summary_result, *notice = _check_kube_pod_status(
            time, value_store, params, section_kube_pod_containers, None, section_kube_pod_lifecycle
        )
        assert isinstance(summary_result, Result)
        assert summary_result.state == expected_state
        assert summary_result.summary.endswith(expected_summary)
        if expected_notice is None:
            assert [] == notice
        else:
            assert isinstance(notice[0], Result)
            assert expected_notice == notice[0].details


@pytest.mark.usefixtures("initialised_item_state")
def test_check_group_order_matters() -> None:
    params = kube_pod_status.Params(
        groups=[
            ("no_levels", [".*"]),
            (("levels", (60, 120)), [".*"]),
        ]
    )
    section_kube_pod_containers = None

    pod_cycles = (
        PodLifeCycle(phase=Phase.PENDING),
        PodLifeCycle(phase=Phase.PENDING),
        PodLifeCycle(phase=Phase.PENDING),
    )

    for section_kube_pod_lifecycle in pod_cycles:
        for summary_result in check_kube_pod_status(
            params, section_kube_pod_containers, None, section_kube_pod_lifecycle
        ):
            assert isinstance(summary_result, Result)
            assert summary_result.state == State.OK
