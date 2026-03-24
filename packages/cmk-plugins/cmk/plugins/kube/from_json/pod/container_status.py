# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import NotRequired, TypedDict

from ...schemata import api


class JSONContainerStateTerminated(TypedDict):
    exitCode: int
    reason: NotRequired[str]
    message: NotRequired[str]
    startedAt: NotRequired[str]
    finishedAt: NotRequired[str]


class JSONContainerStateRunning(TypedDict):
    startedAt: str


class JSONContainerStateWaiting(TypedDict):
    reason: NotRequired[str]
    message: NotRequired[str]


class JSONContainerState(TypedDict):
    terminated: NotRequired[JSONContainerStateTerminated]
    running: NotRequired[JSONContainerStateRunning]
    waiting: NotRequired[JSONContainerStateWaiting]


class JSONContainerStatus(TypedDict):
    state: JSONContainerState
    imageID: str
    image: str
    name: str
    ready: bool
    restartCount: int
    containerID: NotRequired[str]


def pod_containers(
    container_statuses: Sequence[JSONContainerStatus] | None,
) -> dict[str, api.ContainerStatus]:
    result: dict[str, api.ContainerStatus] = {}
    if container_statuses is None:
        return {}
    for status in container_statuses:
        details: (
            JSONContainerStateTerminated
            | JSONContainerStateWaiting
            | JSONContainerStateRunning
            | None
        )
        state: api.ContainerTerminatedState | api.ContainerRunningState | api.ContainerWaitingState
        if (details := status["state"].get("terminated")) is not None:
            state = api.ContainerTerminatedState(
                exit_code=details["exitCode"],
                start_time=(
                    int(api.convert_to_timestamp(started_at))
                    if (started_at := details.get("startedAt"))
                    else None
                ),
                end_time=(
                    int(api.convert_to_timestamp(finished_at))
                    if (finished_at := details.get("finishedAt"))
                    else None
                ),
                reason=details.get("reason"),
                detail=details.get("message"),
            )
        elif (details := status["state"].get("running")) is not None:
            state = api.ContainerRunningState(
                start_time=int(api.convert_to_timestamp(details["startedAt"])),
            )
        elif (details := status["state"].get("waiting")) is not None:
            state = api.ContainerWaitingState(
                reason=details.get("reason"),
                detail=details.get("message"),
            )
        else:
            raise AssertionError(f"Unknown container state {status['state']}")

        result[status["name"]] = api.ContainerStatus(
            container_id=status.get("containerID"),
            image_id=status["imageID"],
            name=status["name"],
            image=status["image"],
            ready=status["ready"],
            state=state,
            restart_count=status["restartCount"],
        )
    return result
