#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt

from dateutil.relativedelta import relativedelta
from pydantic_core import ErrorDetails

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
from cmk.gui.openapi.restful_objects.validators import RequestDataValidator
from cmk.gui.token_auth import AgentRegistrationToken, AuthToken, get_token_store, TokenStore

from .family import AGENT_REGISTRATION_FAMILY
from .model.token import (
    AgentRegistrationTokenMetadata,
    AgentRegistrationTokenObjectModel,
    CreateAgentRegistrationToken,
)
from .utils import PERMISSIONS_AGENT_REGISTRATION


def create_agent_registration_token_v1(
    api_context: ApiContext, body: CreateAgentRegistrationToken
) -> ApiResponse[AgentRegistrationTokenObjectModel]:
    """Creates a new agent registration token and returns its metadata."""
    user.may("wato.manage_hosts")
    user.may("wato.edit_hosts")
    user.may("wato.download_agents")
    user.may("wato.download_all_agents")
    token_store = get_token_store()
    token = issue_agent_registration_token(
        expiration_time=body.expires_at,
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


def issue_agent_registration_token(
    expiration_time: dt.datetime | None,
    comment: str = "",
    token_store: TokenStore | None = None,
) -> AuthToken:
    """Issues a new agent registration token."""
    if token_store is None:
        token_store = get_token_store()
    now = dt.datetime.now(dt.UTC)
    if expiration_time is not None and expiration_time <= now:
        raise RequestDataValidator.format_error_details(
            [
                ErrorDetails(
                    type="value_error",
                    msg=_("The expiration time must be in the future."),
                    loc=("body", "expires_at"),
                    input=expiration_time.isoformat(),
                )
            ]
        ) from None
    return token_store.issue(
        AgentRegistrationToken(),
        issuer=user.ident,
        now=now,
        valid_for=relativedelta(expiration_time, now) if expiration_time else None,
    )


ENDPOINT_CREATE_AGENT_REGISTRATION_TOKEN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("agent_registration_token"),
        link_relation="cmk/create_agent_registration_token",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS_AGENT_REGISTRATION),
    doc=EndpointDoc(family=AGENT_REGISTRATION_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=create_agent_registration_token_v1)},
)
