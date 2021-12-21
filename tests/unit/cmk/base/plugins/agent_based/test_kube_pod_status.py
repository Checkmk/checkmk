#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Optional, Union

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_pod_status import check_kube_pod_status
from cmk.base.plugins.agent_based.utils.k8s import (
    ContainerInfo,
    ContainerRunningState,
    ContainerTerminatedState,
    ContainerWaitingState,
    PodContainers,
)
from cmk.base.plugins.agent_based.utils.kube import PodLifeCycle


def _mocked_container_info_from_state(
    state: Union[ContainerRunningState, ContainerTerminatedState, ContainerWaitingState]
):
    # The check only requires the state field to be populated, therefore all the other fields are
    # filled with some arbitrary values.
    return ContainerInfo(
        id="some_id",
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
            (Result(state=State.OK, summary="Running"),),
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
            (Result(state=State.OK, summary="Pending"),),
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
            (Result(state=State.OK, summary="Succeeded"),),
            id="Container exits with 0, and is not restarted",
        ),
    ],
)
def test_check_k8s_node_kubelet_no_issues_in_containers(
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: Optional[PodLifeCycle],
    expected_result,
) -> None:
    """
    Tested Pods have a single container which is configured correctly and in a good state.
    """
    assert expected_result == tuple(
        check_kube_pod_status(section_kube_pod_containers, section_kube_pod_lifecycle)
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
            (Result(state=State.OK, summary="CrashLoopBackOff"),),
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
            (Result(state=State.OK, summary="Error"),),
            id="Container exits with 1, and is not restarted",
        ),
    ],
)
def test_check_k8s_node_kubelet_failing_container(
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: Optional[PodLifeCycle],
    expected_result,
) -> None:
    """
    Tested Pods with a single failing or misconfigured container.
    """
    assert expected_result == tuple(
        check_kube_pod_status(section_kube_pod_containers, section_kube_pod_lifecycle)
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
            (Result(state=State.OK, summary="Error"),),
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
            (Result(state=State.OK, summary="CrashLoopBackOff"),),
            id="One container has incorrect image name, one container fails with exit code 0",
        ),
        pytest.param(
            None,
            PodLifeCycle(phase="pending"),
            (Result(state=State.OK, summary="Pending"),),
            id="One container is too large to be scheduled, one container fails",
        ),
    ],
)
def test_check_k8s_node_kubelet_multiple_issues(
    section_kube_pod_containers: Optional[PodContainers],
    section_kube_pod_lifecycle: Optional[PodLifeCycle],
    expected_result,
) -> None:
    """
    Tested Pods have two containers with different issues, which are then summarized into a
    single status.
    """
    assert expected_result == tuple(
        check_kube_pod_status(section_kube_pod_containers, section_kube_pod_lifecycle)
    )
