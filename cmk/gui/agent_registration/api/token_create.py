#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.agent_registration.token_util import issue_agent_registration_token
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import collection_href
from cmk.gui.token_auth import get_token_store

from .family import AGENT_REGISTRATION_FAMILY
from .model.token import (
    AgentRegistrationTokenMetadata,
    AgentRegistrationTokenObjectModel,
    CreateAgentRegistrationToken,
)
from .utils import PERMISSIONS_REGISTER_HOST, verify_permissions


def create_agent_registration_token_v1(
    api_context: ApiContext, body: CreateAgentRegistrationToken
) -> ApiResponse[AgentRegistrationTokenObjectModel]:
    """Creates a new agent registration token and returns its metadata."""
    verify_permissions(body.host)
    token_store = get_token_store()
    token = issue_agent_registration_token(
        expiration_time=body.expires_at,
        host=body.host,
        comment=body.comment,
        token_store=token_store,
    )

    return ApiResponse(
        AgentRegistrationTokenObjectModel(
            id=token.token_id,
            domainType="agent_registration_token",
            extensions=AgentRegistrationTokenMetadata.from_internal(token),
            links=[],
        ),
        status_code=201,
    )


ENDPOINT_CREATE_AGENT_REGISTRATION_TOKEN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("agent_registration_token"),
        link_relation="cmk/create_agent_registration_token",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_REGISTER_HOST),
    doc=EndpointDoc(family=AGENT_REGISTRATION_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=create_agent_registration_token_v1)},
)
