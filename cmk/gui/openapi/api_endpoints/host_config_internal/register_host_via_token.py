#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated
from uuid import UUID

import cmk.utils.paths
from cmk.ccc.hostaddress import HostName
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
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import AgentRegistrationToken, get_token_store
from cmk.utils.agent_registration import HostAgentConnectionMode, UUIDLinkManager

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
            status=401,
            title="Authentication required",
            detail="This endpoint requires token authentication.",
        )
    if not isinstance(api_context.token.details, AgentRegistrationToken):
        raise ProblemException(
            status=401,
            title="Authentication required",
            detail="Incorrect token provided. Please provide a token for agent registration.",
        )
    if api_context.token.details.host_name != host_name:
        raise ProblemException(
            status=403,
            title="Forbidden",
            detail="The token was issued for a different host.",
        )
    connection_mode = api_context.token.details.connection_mode
    _link_with_uuid(host_name, body.uuid, connection_mode)
    get_token_store().revoke(api_context.token.token_id)
    return ConnectionMode(connection_mode=connection_mode)


def _link_with_uuid(
    host_name: HostName,
    uuid: UUID,
    connection_mode: HostAgentConnectionMode,
) -> None:
    uuid_link_manager = UUIDLinkManager(
        received_outputs_dir=cmk.utils.paths.received_outputs_dir,
        data_source_dir=cmk.utils.paths.data_source_push_agent_dir,
        r4r_discoverable_dir=cmk.utils.paths.r4r_discoverable_dir,
        uuid_lookup_dir=cmk.utils.paths.uuid_lookup_dir,
    )
    uuid_link_manager.create_link(
        host_name,
        uuid,
        push_configured=connection_mode is HostAgentConnectionMode.PUSH,
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
