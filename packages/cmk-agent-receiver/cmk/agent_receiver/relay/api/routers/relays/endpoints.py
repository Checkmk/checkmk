#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from typing import Annotated

import fastapi
from pydantic import SecretStr

from cmk.agent_receiver.lib.mtls_auth_validator import ExpectedCA, mtls_authorization_dependency
from cmk.agent_receiver.relay.api.routers.relays import dependencies, handlers
from cmk.agent_receiver.relay.api.routers.relays.handlers.forward_monitoring_data import (
    FailedToSendMonitoringDataError,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers.store_crash_report import (
    CrashExtractionTimeoutError,
    UndecodableCrashArchiveError,
)
from cmk.agent_receiver.relay.lib.relays_repository import (
    CheckmkAPIError,
    RelayNotFoundError,
)
from cmk.agent_receiver.relay.lib.shared_types import RelayID, Serial
from cmk.agent_receiver.relay.lib.site_auth import UnsupportedAuthFormatError
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
    except UnsupportedAuthFormatError:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported authorization format. Use 'Bearer <user> <password>' or 'CMK-TOKEN <token>'.",
        )
    except CheckmkAPIError as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            detail=e.msg,
        )


@router.get(
    "/{relay_id}/status",
    status_code=fastapi.status.HTTP_200_OK,
    dependencies=[
        mtls_authorization_dependency(
            "relay_id", fastapi.status.HTTP_403_FORBIDDEN, ExpectedCA.RELAY
        )
    ],
)
async def get_relay_status(
    handler: Annotated[
        handlers.GetRelayStatusHandler, fastapi.Depends(dependencies.get_relay_status_handler)
    ],
    relay_id: str,
) -> relay_protocols.RelayStatusResponse:
    """Get relay status.

    This endpoint returns the relay state by comparing local config and CMK API.
    Only the relay identified by relay_id can access this endpoint (mTLS authorization).

    Returns:
        200 OK: RelayStatusResponse with relay_id and state (CONFIGURED, PENDING_ACTIVATION, PENDING_DELETION)
        404 Not Found: If the relay does not exist in CMK configuration nor in local config
        502 Bad Gateway: If there is an error communicating with the CMK API
    """
    try:
        return handler.process(relay_id=RelayID(relay_id))
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
    "/{relay_id}/csr",
    status_code=fastapi.status.HTTP_200_OK,
    dependencies=[
        mtls_authorization_dependency(
            "relay_id", fastapi.status.HTTP_403_FORBIDDEN, ExpectedCA.RELAY
        )
    ],
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
    dependencies=[
        mtls_authorization_dependency(
            "relay_id", fastapi.status.HTTP_403_FORBIDDEN, ExpectedCA.RELAY
        )
    ],
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
            payload_type=monitoring_data.payload_type,
        )
    except FailedToSendMonitoringDataError as e:
        return fastapi.Response(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            content=f"Failed to forward monitoring data: {e}",
        )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)


@router.post(
    "/{relay_id}/crashes/{crash_type}/{crash_id}",
    status_code=fastapi.status.HTTP_204_NO_CONTENT,
    dependencies=[
        mtls_authorization_dependency(
            "relay_id", fastapi.status.HTTP_403_FORBIDDEN, ExpectedCA.RELAY
        )
    ],
)
async def store_crash_report(
    handler: Annotated[
        handlers.StoreCrashReportHandler,
        fastapi.Depends(dependencies.get_store_crash_report_handler),
    ],
    # The charset keeps ".." out of the path; FastAPI answers a mismatch with 422.
    crash_type: Annotated[str, fastapi.Path(pattern=r"^[a-z0-9_-]+$", max_length=64)],
    crash_id: uuid.UUID,
    request: fastapi.Request,
) -> fastapi.Response:
    """Store a crash report a relay forwarded, for the consolidation cron to pick up."""
    archive = await request.body()
    try:
        await handler.process(crash_type=crash_type, crash_id=str(crash_id), archive=archive)
    except CrashExtractionTimeoutError:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Timed out unpacking the crash archive",
        )
    except UndecodableCrashArchiveError as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"Undecodable crash archive: {e}",
        )
    return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)
