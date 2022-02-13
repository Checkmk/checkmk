#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import itertools
from typing import MutableMapping, Optional, Union

import pytest

from cmk.base.plugins.agent_based import kube_pod_status
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_pod_status import check_kube_pod_status, DEFAULT_PARAMS
from cmk.base.plugins.agent_based.utils.k8s import (
    ContainerRunningState,
    ContainerStatus,
    ContainerTerminatedState,
    ContainerWaitingState,
    PodContainers,
)
from cmk.base.plugins.agent_based.utils.kube import PodLifeCycle

from cmk.gui.plugins.wato.check_parameters import kube_pod_status as wato_kube_pod_status


def _mocked_container_info_from_state(
    state: Union[ContainerRunningState, ContainerTerminatedState, ContainerWaitingState]
):
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


@pytest.mark.parametrize(
    "section_kube_pod_containers, section_kube_pod_lifecycle, expected_result",
    [
        pytest.param(
            PodContainers(
                containers={
                    "running": _mocked_container_info_from_state(
                        ContainerRunningState(type="running", start_time=1639135964)
                    ),
                },
            ),
            PodLifeCycle(phase="running"),
            [Result(state=State.OK, summary="Running")],
            id="A single running container",
        ),
        pytest.param(
            PodContainers(
                containers={
                    "downloading-container": _mocked_container_info_from_state(
                        ContainerWaitingState(
                            type="waiting", reason="ContainerCreating", detail=None
                        )
                    )
                }
            ),
            PodLifeCycle(phase="pending"),
            [Result(state=State.OK, summary="Pending: since 0 seconds")],
            id="Container image is still being downloaded.",
        ),
        pytest.param(
            PodContainers(
                containers={
                    "succeeding-container": _mocked_container_info_from_state(
                        ContainerTerminatedState(
                            type="terminated",
                            exit_code=0,
                            start_time=1639135989,
                            end_time=1639135989,
                            reason="Completed",
                            detail=None,
                        )
                    )
                }
            ),
            PodLifeCycle(phase="succeeded"),
            [Result(state=State.OK, summary="Succeeded")],
            id="Container exits with 0, and is not restarted",
        ),
    ],
)
def test_check_kube_pod_status_no_issues_in_containers(
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: Optional[PodLifeCycle],
    expected_result,
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


@pytest.mark.parametrize(
    "section_kube_pod_containers, section_kube_pod_lifecycle, expected_result",
    [
        pytest.param(
            PodContainers(
                containers={
                    "failing-container": _mocked_container_info_from_state(
                        ContainerWaitingState(
                            type="waiting",
                            reason="CrashLoopBackOff",
                            detail="back-off 5m0s restarting failed container=busybox pod=container-exits-with-1-but-is-restarted_default(c654fe38-6551-473f-8cd1-4a9b06e609de)",
                        )
                    )
                }
            ),
            PodLifeCycle(phase="running"),
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
                            type="terminated",
                            exit_code=1,
                            start_time=1639136018,
                            end_time=1639136018,
                            reason="Error",
                            detail=None,
                        )
                    )
                },
            ),
            PodLifeCycle(phase="failed"),
            [Result(state=State.OK, summary="Error: since 0 seconds")],
            id="Container exits with 1, and is not restarted",
        ),
    ],
)
def test_check_kube_pod_status_failing_container(
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: Optional[PodLifeCycle],
    expected_result,
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


@pytest.mark.parametrize(
    "section_kube_pod_containers, section_kube_pod_lifecycle, expected_result",
    [
        pytest.param(
            PodContainers(
                containers={
                    "failing-container": _mocked_container_info_from_state(
                        ContainerTerminatedState(
                            type="terminated",
                            exit_code=1,
                            start_time=1639136911,
                            end_time=1639136911,
                            reason="Error",
                            detail=None,
                        )
                    ),
                    "running": _mocked_container_info_from_state(
                        ContainerTerminatedState(
                            type="terminated",
                            exit_code=0,
                            start_time=1639136913,
                            end_time=1639137513,
                            reason="Completed",
                            detail=None,
                        )
                    ),
                }
            ),
            PodLifeCycle(phase="failed"),
            [Result(state=State.OK, summary="Error: since 0 seconds")],
            id="Both containers are terminating, one with exit code 1, the other with exit code 0.",
        ),
        pytest.param(
            PodContainers(
                containers={
                    "failing-container": _mocked_container_info_from_state(
                        state=ContainerWaitingState(
                            type="waiting",
                            reason="CrashLoopBackOff",
                            detail="back-off 5m0s restarting failed container=busybox pod=failingcontainer-imagepullbackerror_default(e7437bfb-3043-44a0-a071-4221ab43c550)",
                        )
                    ),
                    "wrong-image-name": _mocked_container_info_from_state(
                        state=ContainerWaitingState(
                            type="waiting",
                            reason="ImagePullBackOff",
                            detail='Back-off pulling image "busybox1"',
                        )
                    ),
                }
            ),
            PodLifeCycle(phase="pending"),
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
            PodLifeCycle(phase="pending"),
            [Result(state=State.OK, summary="Pending: since 0 seconds")],
            id="One container is too large to be scheduled, one container fails",
        ),
    ],
)
def test_check_kube_pod_status_multiple_issues(
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: Optional[PodLifeCycle],
    expected_result,
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


@pytest.fixture(name="get_value_store")
def fixture_get_value_store(mocker):
    value_store: MutableMapping[str, float] = {}
    get_value_store_mock = mocker.MagicMock(return_value=value_store)
    mocker.patch.object(kube_pod_status, "get_value_store", get_value_store_mock)
    return get_value_store_mock


@pytest.fixture(name="time_time")
def fixture_time(mocker):
    mocked_time = mocker.Mock()
    mocked_time.time = mocker.Mock(side_effect=itertools.count(0.1, 60.1))
    mocker.patch.object(kube_pod_status, "time", mocked_time)
    return mocked_time


def test_check_alert_if_pending_too_long(get_value_store, time_time) -> None:

    section_kube_pod_containers = None
    section_kube_pod_lifecycle = PodLifeCycle(phase="pending")
    params: kube_pod_status.Params = {"Pending": ("levels", (60, 120))}

    expected_results = (
        (State.OK, "0 seconds"),
        (State.WARN, "1 minute 0 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)"),
        (State.CRIT, "2 minutes 0 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)"),
    )
    for expected_result in expected_results:
        expected_state, expected_message = expected_result
        for result in check_kube_pod_status(
            params, section_kube_pod_containers, None, section_kube_pod_lifecycle
        ):
            assert isinstance(result, Result)
            assert result.state == expected_state
            assert result.summary.endswith(expected_message)


@pytest.mark.parametrize(
    "section_kube_pod_init_containers, section_kube_pod_containers, section_kube_pod_lifecycle, expected_result",
    [
        pytest.param(
            PodContainers(
                containers={
                    "failing-container": _mocked_container_info_from_state(
                        ContainerTerminatedState(
                            type="terminated",
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
            PodLifeCycle(phase="pending"),
            "Init:Error",
            id="Both containers have an error, but the second container is not intialized",
        ),
    ],
)
def test_check_kube_pod_stauts_init_container_broken(
    section_kube_pod_init_containers: PodContainers,
    section_kube_pod_containers: PodContainers,
    section_kube_pod_lifecycle: Optional[PodLifeCycle],
    expected_result,
) -> None:
    """
    Tested Pods has a failing init-container.
    """
    for result in check_kube_pod_status(
        DEFAULT_PARAMS,
        section_kube_pod_containers,
        section_kube_pod_init_containers,
        section_kube_pod_lifecycle,
    ):
        assert isinstance(result, Result)
        assert result.summary.startswith(expected_result)


def test_check_alert_resets(get_value_store, time_time) -> None:

    params: kube_pod_status.Params = {
        "Pending": ("levels", (60, 120)),
        "Running": ("levels", (60, 120)),
    }
    section_kube_pod_containers = None

    pod_cycles = (
        PodLifeCycle(phase="pending"),
        PodLifeCycle(phase="pending"),
        PodLifeCycle(phase="running"),
        PodLifeCycle(phase="pending"),
    )

    expected_results = (
        (State.OK, "0 seconds"),
        (
            State.WARN,
            "1 minute 0 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
        ),
        (State.OK, "0 seconds"),
        (State.OK, "0 seconds"),
    )

    for expected_result, section_kube_pod_lifecycle in zip(expected_results, pod_cycles):
        expected_state, expected_message = expected_result
        for result in check_kube_pod_status(
            params, section_kube_pod_containers, None, section_kube_pod_lifecycle
        ):
            assert isinstance(result, Result)
            assert result.state == expected_state
            assert result.summary.endswith(expected_message)


def test_check_variables_in_check_parameters_and_agent_based_plugins_agree() -> None:
    """Variables have to be defined twice in order to preserve cmk-module-layer"""
    assert wato_kube_pod_status.CONTAINER_STATUSES == kube_pod_status.CONTAINER_STATUSES
    assert wato_kube_pod_status.INIT_STATUSES == kube_pod_status.INIT_STATUSES
    assert wato_kube_pod_status.DESIRED_PHASE == kube_pod_status.DESIRED_PHASE
    assert wato_kube_pod_status.UNDESIRED_PHASE == kube_pod_status.UNDESIRED_PHASE
