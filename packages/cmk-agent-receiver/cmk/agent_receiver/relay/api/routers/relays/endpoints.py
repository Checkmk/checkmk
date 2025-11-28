#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

import fastapi
from pydantic import SecretStr

from cmk.agent_receiver.relay.api.routers.relays.dependencies import (
    get_forward_monitoring_data_handler,
    get_register_relay_handler,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers import (
    ForwardMonitoringDataHandler,
    RegisterRelayHandler,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers.forward_monitoring_data import (
    FailedToSendMonitoringDataError,
)
from cmk.agent_receiver.relay.lib.check_relay import check_relay
from cmk.agent_receiver.relay.lib.relays_repository import CheckmkAPIError
from cmk.relay_protocols.monitoring_data import MonitoringData
from cmk.relay_protocols.relays import RelayRegistrationRequest, RelayRegistrationResponse

router = fastapi.APIRouter()


@router.post("/", status_code=fastapi.status.HTTP_200_OK)
async def register_relay(
    handler: Annotated[RegisterRelayHandler, fastapi.Depends(get_register_relay_handler)],
    authorization: Annotated[SecretStr, fastapi.Header()],
    payload: RelayRegistrationRequest,
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
    try:
        return handler.process(authorization, request=payload)
    except CheckmkAPIError as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            detail=e.msg,
        )


@router.post(
    "/{relay_id}/monitoring",
    status_code=fastapi.status.HTTP_204_NO_CONTENT,
    dependencies=[fastapi.Depends(check_relay)],
)
async def forward_monitoring_data(
    monitoring_data: MonitoringData,
    handler: Annotated[
        ForwardMonitoringDataHandler, fastapi.Depends(get_forward_monitoring_data_handler)
    ],
) -> fastapi.Response:
    """
    Forward monitoring data to CMC for a specific relay and host.
    """
    try:
        handler.process(
            payload=monitoring_data.payload,
            host=monitoring_data.host,
            config_serial=monitoring_data.serial,
            timestamp=monitoring_data.timestamp,
        )
    except FailedToSendMonitoringDataError as e:
        return fastapi.Response(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            content=f"Failed to forward monitoring data: {e}",
        )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
