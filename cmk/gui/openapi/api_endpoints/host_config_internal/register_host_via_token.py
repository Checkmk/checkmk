#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, UTC
from http import HTTPStatus
from typing import Annotated

from cmk.ccc.hostaddress import HostName
from cmk.gui.openapi.api_endpoints.host_config import HOST_CONFIG_FAMILY
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import (
    AgentRegistrationToken,
    get_token_store,
    TokenExpired,
    TokenRevoked,
    TokenUseAlreadyConsumed,
    UnknownToken,
)
from cmk.gui.watolib.agent_registration import link_uuid_of_registration
from cmk.utils.agent_registration import HostAgentConnectionMode

from .models.request_models import RegisterHost
from .models.response_models import ConnectionMode


def register_host_via_token_v1(
    api_context: ApiContext,
    host_name: Annotated[
        Annotated[
            HostName,
            TypedPlainValidator(str, HostName),
        ],
        PathParam(description="A host name.", example="my_host"),
    ],
    body: RegisterHost,
) -> ConnectionMode:
    """Register a host via a one-time agent registration token, i.e. link it to a UUID.

    The token has been pre-authorized on the issuing site (host existence,
    cluster check, user permissions, target site). This endpoint therefore
    trusts the token's payload and does not re-load the host from the local
    WATO config — that allows registration to succeed even before the host
    config has been replicated to a remote site via Activate Changes.
    """
    if not api_context.token:
        raise ProblemException(
            status=HTTPStatus.UNAUTHORIZED,
            title="Authentication required",
            detail="This endpoint requires token authentication.",
        )
    if not isinstance(api_context.token.details, AgentRegistrationToken):
        raise ProblemException(
            status=HTTPStatus.UNAUTHORIZED,
            title="Authentication required",
            detail="Incorrect token provided. Please provide a token for agent registration.",
        )
    if api_context.token.details.host_name != host_name:
        raise ProblemException(
            status=HTTPStatus.FORBIDDEN,
            title="Forbidden",
            detail="The token was issued for a different host.",
        )
    connection_mode = api_context.token.details.connection_mode
    try:
        with get_token_store().agent_registration_use(
            api_context.token.token_id, "host_registration", datetime.now(UTC)
        ):
            link_uuid_of_registration(
                host_name,
                body.uuid,
                push_configured=connection_mode is HostAgentConnectionMode.PUSH,
            )
    except TokenUseAlreadyConsumed:
        raise _token_already_used()
    except UnknownToken, TokenExpired, TokenRevoked:
        raise ProblemException(
            status=HTTPStatus.UNAUTHORIZED,
            title="Authentication required",
            detail="The token is no longer valid.",
        )
    return ConnectionMode(connection_mode=connection_mode)


def _token_already_used() -> ProblemException:
    return ProblemException(
        status=HTTPStatus.FORBIDDEN,
        title="Token already used",
        detail="This token has already been used to register this host. "
        "Please issue a new token to register again.",
    )


ENDPOINT_REGISTER_HOST_VIA_TOKEN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href(
            "host_config_internal", "{host_name}", action_name="register_via_token"
        ),
        link_relation="cmk/register_token",
        method="put",
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=HOST_CONFIG_FAMILY.name, group="Checkmk Internal"),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=register_host_via_token_v1)},
    allowed_tokens={"agent_registration"},
)
