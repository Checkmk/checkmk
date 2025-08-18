#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

import fastapi

from cmk.agent_receiver.relay_backend.api.dependencies.get_relay_tasks_handler import (
    get_relay_tasks_handler,
)
from cmk.agent_receiver.relay_backend.api.dependencies.register_relay_handler import (
    get_register_relay_handler,
)
from cmk.agent_receiver.relay_backend.api.routers.base_router import RELAY_ROUTER
from cmk.agent_receiver.relay_backend.api.routers.relays.handlers.get_relay_tasks import (
    GetRelayTasksHandler,
)
from cmk.agent_receiver.relay_backend.api.routers.relays.handlers.register_relay import (
    RegisterRelayHandler,
    RelayAlreadyRegisteredError,
)
from cmk.relay_protocols.relays import RelayRegistrationRequest
from cmk.relay_protocols.tasks import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
    TaskUpdateRequest,
)


@RELAY_ROUTER.post("/", status_code=fastapi.status.HTTP_200_OK)
async def register_relay(
    request: RelayRegistrationRequest,
    handler: Annotated[RegisterRelayHandler, fastapi.Depends(get_register_relay_handler)],
) -> fastapi.Response:
    """Register a new relay entity.

    This endpoint allows relay entities to register themselves with the Agent Receiver.
    The relay provides its ID, name, certificate signing request, and auth token.

    Args:
        request: RelayRegistrationRequest containing relay registration data

    Returns:
        Success message confirming relay registration

    Note:
        - Relay ID uniqueness is controlled during registration
        - Collision with existing relay IDs is not allowed
    """
    # Business logic for relay registration intentionally not implemented
    # - Validate relay_id uniqueness
    # - Process CSR
    # - Store relay information
    # - Generate and return appropriate certificates

    try:
        handler.process(request.relay_id)
    except RelayAlreadyRegisteredError:
        return fastapi.Response(
            status_code=fastapi.status.HTTP_409_CONFLICT, content="Relay ID already registered"
        )
    return fastapi.Response(
        status_code=fastapi.status.HTTP_200_OK, content="Relay registered successfully"
    )


@RELAY_ROUTER.delete("/{relay_id}")
async def unregister_relay(relay_id: str) -> None:
    """Unregister a relay entity.

    This endpoint allows relay entities to be unregistered from the Agent Receiver.
    Deletion can happen regardless of existing tasks for that relay.

    Args:
        relay_id: UUID of the relay to unregister

    Returns:
        Success message confirming relay unregistration

    Note:
        - Relay can be deleted regardless of existing tasks
        - Tasks belonging to deleted relay may need cleanup
    """
    # Business logic for relay unregistration intentionally not implemented
    # - Validate relay exists
    # - Remove relay information
    # - Handle cleanup of associated tasks (if needed)

    raise NotImplementedError("Relay unregistration business logic not implemented")


@RELAY_ROUTER.post(
    "/{relay_id}/tasks/",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": TaskCreateResponse},
    },
)
async def create_task(relay_id: str, request: TaskCreateRequest) -> TaskCreateResponse:
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

    raise NotImplementedError("Task creation business logic not implemented")


@RELAY_ROUTER.patch(
    "/{relay_id}/tasks/{task_id}",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": TaskResponse},
    },
)
async def update_task(relay_id: str, task_id: str, request: TaskUpdateRequest) -> TaskResponse:
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


@RELAY_ROUTER.get("/{relay_id}/tasks")
async def get_tasks(
    relay_id: str,
    handler: Annotated[GetRelayTasksHandler, fastapi.Depends(get_relay_tasks_handler)],
    status: TaskStatus | None = fastapi.Query(None, description="Filter tasks by status"),
) -> TaskListResponse:
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

    return handler.process(relay_id, status)
