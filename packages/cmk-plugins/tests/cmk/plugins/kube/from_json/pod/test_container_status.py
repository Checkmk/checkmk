# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.kube.from_json.pod.container_status import pod_containers
from cmk.plugins.kube.schemata.api import (
    ContainerRunningState,
    ContainerTerminatedState,
    ContainerWaitingState,
)


def test_pod_containers_none() -> None:
    assert pod_containers(None) == {}


def test_pod_containers_empty() -> None:
    assert pod_containers([]) == {}


def test_running_container() -> None:
    result = pod_containers(
        [
            {
                "name": "my-container",
                "state": {"running": {"startedAt": "2026-03-19T17:34:38Z"}},
                "imageID": "docker.io/image@sha256:abc",
                "image": "docker.io/image:latest",
                "ready": True,
                "restartCount": 0,
                "containerID": "containerd://abc123",
            }
        ]
    )
    assert "my-container" in result
    status = result["my-container"]
    assert isinstance(status.state, ContainerRunningState)
    assert status.state.start_time == 1773941678
    assert status.ready is True
    assert status.restart_count == 0
    assert status.container_id == "containerd://abc123"
    assert status.image_id == "docker.io/image@sha256:abc"


def test_terminated_container() -> None:
    result = pod_containers(
        [
            {
                "name": "init",
                "state": {
                    "terminated": {
                        "exitCode": 0,
                        "reason": "Completed",
                        "message": "done",
                        "startedAt": "2026-03-19T17:34:38Z",
                        "finishedAt": "2026-03-19T17:34:40Z",
                    },
                },
                "imageID": "docker.io/init@sha256:def",
                "image": "docker.io/init:1.0",
                "ready": False,
                "restartCount": 1,
            }
        ]
    )
    status = result["init"]
    assert isinstance(status.state, ContainerTerminatedState)
    assert status.state.exit_code == 0
    assert status.state.reason == "Completed"
    assert status.state.detail == "done"
    assert status.state.start_time == 1773941678
    assert status.state.end_time == 1773941680
    assert status.container_id is None
    assert status.restart_count == 1


def test_terminated_container_minimal() -> None:
    """
    Terminated with only exitCode -- no reason, message, startedAt, finishedAt.
    """
    result = pod_containers(
        [
            {
                "name": "crash",
                "state": {"terminated": {"exitCode": 137}},
                "imageID": "",
                "image": "busybox",
                "ready": False,
                "restartCount": 5,
            }
        ]
    )
    status = result["crash"]
    assert isinstance(status.state, ContainerTerminatedState)
    assert status.state.exit_code == 137
    assert status.state.start_time is None
    assert status.state.end_time is None
    assert status.state.reason is None
    assert status.state.detail is None


def test_waiting_container() -> None:
    result = pod_containers(
        [
            {
                "name": "pending",
                "state": {"waiting": {"reason": "ImagePullBackOff", "message": "pull failed"}},
                "imageID": "",
                "image": "nonexistent:latest",
                "ready": False,
                "restartCount": 0,
            }
        ]
    )
    status = result["pending"]
    assert isinstance(status.state, ContainerWaitingState)
    assert status.state.reason == "ImagePullBackOff"
    assert status.state.detail == "pull failed"


def test_waiting_container_reason_only() -> None:
    result = pod_containers(
        [
            {
                "name": "pending",
                "state": {"waiting": {"reason": "ContainerCreating"}},
                "imageID": "",
                "image": "busybox",
                "ready": False,
                "restartCount": 0,
            }
        ]
    )
    status = result["pending"]
    assert isinstance(status.state, ContainerWaitingState)
    assert status.state.reason == "ContainerCreating"
    assert status.state.detail is None


def test_empty_waiting_dict() -> None:
    """
    An empty waiting dict is valid -- reason and message are both optional.
    """
    result = pod_containers(
        [
            {
                "name": "pending",
                "state": {"waiting": {}},
                "imageID": "",
                "image": "busybox",
                "ready": False,
                "restartCount": 0,
            }
        ]
    )
    status = result["pending"]
    assert isinstance(status.state, ContainerWaitingState)
    assert status.state.reason is None
    assert status.state.detail is None


def test_unknown_state_raises() -> None:
    with pytest.raises(AssertionError, match="Unknown container state"):
        pod_containers(
            [
                {
                    "name": "broken",
                    "state": {},
                    "imageID": "",
                    "image": "busybox",
                    "ready": False,
                    "restartCount": 0,
                }
            ]
        )


def test_multiple_containers() -> None:
    result = pod_containers(
        [
            {
                "name": "web",
                "state": {"running": {"startedAt": "2026-03-19T17:34:38Z"}},
                "imageID": "img1",
                "image": "nginx",
                "ready": True,
                "restartCount": 0,
            },
            {
                "name": "sidecar",
                "state": {"running": {"startedAt": "2026-03-19T17:34:39Z"}},
                "imageID": "img2",
                "image": "envoy",
                "ready": True,
                "restartCount": 0,
            },
        ]
    )
    assert set(result.keys()) == {"web", "sidecar"}
