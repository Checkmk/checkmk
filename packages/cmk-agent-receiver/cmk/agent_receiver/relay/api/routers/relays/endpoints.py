#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

import fastapi
from pydantic import SecretStr

from cmk.agent_receiver.lib.mtls_auth_validator import mtls_authorization_dependency
from cmk.agent_receiver.relay.api.routers.relays import dependencies, handlers
from cmk.agent_receiver.relay.api.routers.relays.handlers.forward_monitoring_data import (
    FailedToSendMonitoringDataError,
)
from cmk.agent_receiver.relay.lib.relays_repository import CheckmkAPIError, RelayNotFoundError
from cmk.agent_receiver.relay.lib.shared_types import RelayID, Serial
from cmk.relay_protocols import relays as relay_protocols
from cmk.relay_protocols.monitoring_data import MonitoringData

router = fastapi.APIRouter()


@router.post("/", status_code=fastapi.status.HTTP_200_OK)
async def register_relay(
    handler: Annotated[
        handlers.RegisterRelayHandler, fastapi.Depends(dependencies.get_register_relay_handler)
    ],
    authorization: Annotated[SecretStr, fastapi.Header()],
    payload: relay_protocols.RelayRegistrationRequest,
) -> relay_protocols.RelayRegistrationResponse:
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
    "/{relay_id}/csr",
    status_code=fastapi.status.HTTP_200_OK,
    dependencies=[mtls_authorization_dependency("relay_id")],
)
async def refresh_cert(
    handler: Annotated[
        handlers.RefreshCertHandler, fastapi.Depends(dependencies.get_refresh_cert_handler)
    ],
    relay_id: str,
    payload: relay_protocols.RelayRefreshCertRequest,
) -> relay_protocols.RelayRefreshCertResponse:
    try:
        return handler.process(relay_id=RelayID(relay_id), request=payload)
    except RelayNotFoundError:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Relay {relay_id} not found",
        )
    except CheckmkAPIError as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            detail=e.msg,
        )


@router.post(
    "/{relay_id}/monitoring",
    status_code=fastapi.status.HTTP_204_NO_CONTENT,
    dependencies=[mtls_authorization_dependency("relay_id")],
)
async def forward_monitoring_data(
    monitoring_data: MonitoringData,
    handler: Annotated[
        handlers.ForwardMonitoringDataHandler,
        fastapi.Depends(dependencies.get_forward_monitoring_data_handler),
    ],
) -> fastapi.Response:
    """
    Forward monitoring data to CMC for a specific relay and host.
    """
    try:
        handler.process(
            payload=monitoring_data.payload,
            host=monitoring_data.host,
            config_serial=Serial(monitoring_data.serial),
            timestamp=monitoring_data.timestamp,
            service=monitoring_data.service,
        )
    except FailedToSendMonitoringDataError as e:
        return fastapi.Response(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            content=f"Failed to forward monitoring data: {e}",
        )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
