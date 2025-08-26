#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated
from uuid import UUID

import fastapi

from cmk.agent_receiver.relay.api.routers.tasks.dependencies import (
    get_create_task_handler,
    get_relay_tasks_handler,
)
from cmk.agent_receiver.relay.api.routers.tasks.handlers import (
    CreateTaskHandler,
    GetRelayTasksHandler,
    RelayNotFoundError,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import TaskStatus
from cmk.agent_receiver.relay.api.routers.tasks.serializers import (
    TaskListResponseSerializer,
)
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.relay_protocols import tasks as tasks_protocol

router = fastapi.APIRouter()


@router.post(
    "/{relay_id}/tasks",
    status_code=fastapi.status.HTTP_200_OK,
    responses={
        200: {"model": tasks_protocol.TaskCreateResponse},
    },
)
async def create_task(
    relay_id: str,
    _request: tasks_protocol.TaskCreateRequest,  # TODO: Remove underscore when using it
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
    # Business logic for task creation intentionally not implemented
    # - Validate relay exists
    # - Validate task type and payload
    # - Check maximum task limit for the Relay
    # - Create task
    #   - Generate unique task ID
    #   - Set creation and last update timestamps
    #   - Set task type and payload from request
    #   - Set status to PENDING
    # - Store task in database

    try:
        task_id = handler.process(RelayID(relay_id))
    except RelayNotFoundError:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Relay with ID {relay_id} not found",
        )
    return tasks_protocol.TaskCreateResponse(task_id=UUID(task_id))


@router.patch(
    "/{relay_id}/tasks/{task_id}",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": tasks_protocol.TaskResponse},
    },
)
async def update_task(
    relay_id: str, task_id: str, request: tasks_protocol.TaskUpdateRequest
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
    # Business logic for task update intentionally not implemented
    # - Validate relay exists
    # - Validate task exists and belongs to Relay
    # - Validate TaskUpdateRequest
    #   - Check result_type
    #   - Check result payload / Error
    # - Update task with results
    # - Update status based on result_type
    # - Update last_update_timestamp
    # - Store updated task

    raise NotImplementedError("Task update business logic not implemented")


@router.get("/{relay_id}/tasks")
async def get_tasks(
    relay_id: str,
    handler: Annotated[GetRelayTasksHandler, fastapi.Depends(get_relay_tasks_handler)],
    status: tasks_protocol.TaskStatus | None = fastapi.Query(
        None, description="Filter tasks by status"
    ),
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
    # Business logic for task listing intentionally not implemented
    # - Validate relay exists
    # - Apply status filter if provided
    # - Note: we can remove expired tasks based on expiration time configuration here
    #         instead of having a separate cleanup task
    # - Return filtered task list
    try:
        tasks = handler.process(RelayID(relay_id), TaskStatus(status.value) if status else None)
    except RelayNotFoundError:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Relay not found"
        ) from None
    return TaskListResponseSerializer.serialize(tasks)
