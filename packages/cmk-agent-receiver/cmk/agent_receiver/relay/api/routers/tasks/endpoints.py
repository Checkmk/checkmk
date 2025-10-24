#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

import fastapi

from cmk.agent_receiver.log import bound_contextvars
from cmk.agent_receiver.relay.api.routers.tasks.dependencies import (
    get_activate_config_handler,
    get_create_task_handler,
    get_relay_task_handler,
    get_relay_tasks_handler,
    get_update_task_handler,
)
from cmk.agent_receiver.relay.api.routers.tasks.handlers import (
    ActivateConfigHandler,
    CreateTaskHandler,
    GetRelayTaskHandler,
    GetRelayTasksHandler,
    UpdateTaskHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    FetchSpec,
    ResultType,
    TaskStatus,
)
from cmk.agent_receiver.relay.api.routers.tasks.serializers import (
    TaskListResponseSerializer,
    TaskResponseSerializer,
)
from cmk.agent_receiver.relay.lib.check_relay import check_relay
from cmk.agent_receiver.relay.lib.relays_repository import CheckmkAPIError
from cmk.agent_receiver.relay.lib.shared_types import RelayID, Serial, TaskID
from cmk.relay_protocols import tasks as tasks_protocol

router = fastapi.APIRouter()


@router.post(
    "/{relay_id}/tasks",
    status_code=fastapi.status.HTTP_200_OK,
    responses={
        200: {"model": tasks_protocol.TaskCreateResponse},
    },
    dependencies=[fastapi.Depends(check_relay)],
)
async def create_task_endpoint(
    relay_id: str,
    request: tasks_protocol.TaskCreateRequest,
    handler: Annotated[CreateTaskHandler, fastapi.Depends(get_create_task_handler)],
) -> tasks_protocol.TaskCreateResponse:
    """Create a new Service Fetching Task for a specific relay.

    This endpoint allows clients to POST new tasks to be assigned to a specific relay.
    Tasks are created with PENDING status by default.

    Args:
        relay_id: UUID of the relay to assign the task to
        request: TaskCreateRequest containing task type and payload

    Returns:
        TaskCreateResponse with the generated task ID

    Raises:
        HTTPException: If relay doesn't exist or maximum task limit reached

    Note:
        - Tasks are created with PENDING status
        - Task IDs are unique
        - Maximum number of stored tasks has limits
    """

    # In case a new TaskCreateRequestSpec is added in the future, extend this match-case
    # match request.spec:
    spec = FetchSpec(
        payload=request.spec.payload,
        timeout=request.spec.timeout,
    )

    try:
        task_id = handler.process(RelayID(relay_id), spec)
    except CheckmkAPIError as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            detail=e.msg,
        )
    return tasks_protocol.TaskCreateResponse(task_id=task_id)


@router.patch(
    "/{relay_id}/tasks/{task_id}",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": tasks_protocol.TaskResponse},
    },
    dependencies=[fastapi.Depends(check_relay)],
)
async def update_task(
    relay_id: str,
    task_id: str,
    request: tasks_protocol.TaskUpdateRequest,
    handler: Annotated[UpdateTaskHandler, fastapi.Depends(get_update_task_handler)],
) -> tasks_protocol.TaskResponse:
    """Update a task with results.

    This endpoint allows relays to PATCH tasks with their execution results.
    The task status will be updated based on the result type:
    - FINISHED if result_type = OK
    - FAILED if result_type = ERROR

    Args:
        relay_id: UUID of the relay that owns the task
        task_id: UUID of the task to update
        request: TaskUpdateRequest containing result data

    Returns:
        Updated Task object

    Raises:
        HTTPException: If relay or task doesn't exist

    Note:
        - Updates last_update_timestamp
        - Status changes based on result_type
        - Tasks with results can trigger expiration calculation
    """
    try:
        with bound_contextvars(task_id=task_id):
            updated_task = handler.process(
                relay_id=RelayID(relay_id),
                task_id=TaskID(task_id),
                result_type=ResultType(request.result_type.value),
                result_payload=request.result_payload,
            )
    except CheckmkAPIError as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            detail=e.msg,
        )
    return TaskResponseSerializer.serialize(updated_task)


# TODO try to use dependency to check the serial mismatch
@router.get("/{relay_id}/tasks", dependencies=[fastapi.Depends(check_relay)])
async def get_tasks_endpoint(
    relay_id: str,
    handler: Annotated[GetRelayTasksHandler, fastapi.Depends(get_relay_tasks_handler)],
    relay_serial: Annotated[str | None, fastapi.Header(alias=tasks_protocol.HEADERS.SERIAL)] = None,
    status: Annotated[
        tasks_protocol.TaskStatus | None, fastapi.Query(description="Filter tasks by status")
    ] = None,
) -> tasks_protocol.TaskListResponse:
    """Get tasks for a relay, optionally filtered by status.

    This endpoint allows clients (especially relays) to GET tasks assigned to them.
    Most commonly used with status=pending to get pending tasks.

    Args:
        relay_id: UUID of the relay to get tasks for
        status: Optional status filter (e.g., 'pending', 'finished', 'failed')

    Returns:
        TaskListResponse containing list of tasks

    Raises:
        HTTPException: If relay doesn't exist

    Note:
        - Tasks are subject to expiration based on last_update_timestamp
        - Expired tasks are automatically removed
    """
    try:
        tasks = handler.process(
            RelayID(relay_id),
            TaskStatus(status.value) if status else None,
            relay_serial=Serial(relay_serial) if relay_serial else None,
        )
    except CheckmkAPIError as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            detail=e.msg,
        )
    return TaskListResponseSerializer.serialize(tasks)


@router.get("/{relay_id}/tasks/{task_id}", dependencies=[fastapi.Depends(check_relay)])
async def get_task_endpoint(
    relay_id: str,
    task_id: str,
    handler: Annotated[GetRelayTaskHandler, fastapi.Depends(get_relay_task_handler)],
) -> tasks_protocol.TaskResponse:
    """
    Get a specific task for a relay

    Args:
        relay_id: UUID of the relay
        task_id: UUID of the task

    Returns:
        TaskResponse containing task details
    """
    try:
        with bound_contextvars(task_id=task_id):
            task = handler.process(RelayID(relay_id), TaskID(task_id))
    except CheckmkAPIError as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            detail=e.msg,
        )

    return TaskResponseSerializer.serialize(task)


@router.post("/activate-config", status_code=fastapi.status.HTTP_200_OK)
async def create_relay_config_tasks(
    handler: Annotated[ActivateConfigHandler, fastapi.Depends(get_activate_config_handler)],
) -> tasks_protocol.TaskListResponse:
    """
    Create a relay configuration task for every registered relay.

    The received RelayConfigTask payload is used to create and persist an individual task per relay
    so that each relay can load its configuration independently.

    Args:
        payload: RelayConfigTask containing the configuration data template.

    Returns:
        TaskListResponse containing the list of created tasks.
    """
    created_tasks = handler.process()
    return TaskListResponseSerializer.serialize(created_tasks)
