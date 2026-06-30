#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.agent_registration.token_util import (
    issue_agent_registration_token,
    reject_if_cluster_host,
)
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
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
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.site_config import site_is_local
from cmk.gui.token_auth import get_token_store
from cmk.gui.watolib.agent_token_automations import (
    AgentRegistrationTokenCreateRequest,
    forward_token_create,
)
from cmk.utils.agent_registration import connection_mode_from_host_config

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
    reject_if_cluster_host(body.host)
    connection_mode = connection_mode_from_host_config(body.host.effective_attributes())

    if body.site_id is not None:
        site_config = api_context.config.sites.get(body.site_id)
        if site_config is None:
            raise ProblemException(
                status=400,
                title="Unknown site",
                detail=_('No site with ID "%s" is configured.') % body.site_id,
            )
        if not site_is_local(site_config):
            forwarded = forward_token_create(
                site_id=body.site_id,
                site_config=site_config,
                command="agent-registration-token-create",
                request_payload=AgentRegistrationTokenCreateRequest(
                    issuer=user.ident,
                    host_name=body.host.name(),
                    connection_mode=connection_mode,
                    expires_at=body.expires_at,
                    comment=body.comment,
                ),
                debug=api_context.config.debug,
            )
            return ApiResponse(
                AgentRegistrationTokenObjectModel(
                    id=forwarded.id,
                    domainType="agent_registration_token",
                    extensions=AgentRegistrationTokenMetadata(
                        comment=body.comment,
                        host_name=body.host.name(),
                        issued_at=forwarded.issued_at,
                        expires_at=forwarded.expires_at,
                    ),
                    links=[],
                ),
                status_code=201,
            )

    token = issue_agent_registration_token(
        expiration_time=body.expires_at,
        host=body.host,
        comment=body.comment,
        token_store=get_token_store(),
        connection_mode=connection_mode,
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
