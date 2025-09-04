#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

import fastapi

from cmk.agent_receiver.relay.api.routers.relays.dependencies import (
    get_register_relay_handler,
    get_unregister_relay_handler,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers import (
    RegisterRelayHandler,
    RelayNotFoundError,
    UnregisterRelayHandler,
)
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.relay_protocols.relays import RelayRegistrationResponse

router = fastapi.APIRouter()


@router.post("/", status_code=fastapi.status.HTTP_200_OK)
async def register_relay(
    handler: Annotated[RegisterRelayHandler, fastapi.Depends(get_register_relay_handler)],
) -> RelayRegistrationResponse:
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
    relay_id = handler.process()
    return RelayRegistrationResponse(relay_id=relay_id)


@router.delete("/{relay_id}")
async def unregister_relay(
    relay_id: str,
    handler: Annotated[UnregisterRelayHandler, fastapi.Depends(get_unregister_relay_handler)],
) -> fastapi.Response:
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
        - This endpoint is idempotent
    """
    try:
        handler.process(RelayID(relay_id))
    except RelayNotFoundError:
        # When the relay is not found we chose to return a 200 to make this endpoint idempotent
        return fastapi.Response(
            status_code=fastapi.status.HTTP_200_OK, content="Relay unregistered successfully"
        )

    return fastapi.Response(
        status_code=fastapi.status.HTTP_200_OK, content="Relay unregistered successfully"
    )
