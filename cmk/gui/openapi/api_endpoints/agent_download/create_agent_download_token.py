#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt

from dateutil.relativedelta import relativedelta

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
from cmk.gui.openapi.shared_endpoint_families.agent import AGENTS_FAMILY
from cmk.gui.token_auth import AgentDownloadToken, AuthToken, get_token_store
from cmk.gui.utils import permission_verification as permissions

from .models.token import (
    AgentDownloadTokenMetadata,
    AgentDownloadTokenObjectModel,
    CreateAgentDownloadToken,
)

_DOWNLOAD_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.use"),
    ]
)


def _issue_agent_download_token(expiration_time: dt.datetime | None) -> AuthToken:
    token_store = get_token_store()
    now = dt.datetime.now(dt.UTC)
    return token_store.issue(
        AgentDownloadToken(),
        issuer=user.ident,
        now=now,
        valid_for=relativedelta(expiration_time, now) if expiration_time else None,
    )


def create_agent_download_token_v1(
    api_context: ApiContext, body: CreateAgentDownloadToken
) -> ApiResponse[AgentDownloadTokenObjectModel]:
    """Creates a new agent download token and returns its metadata."""
    user.need_permission("wato.use")
    token = _issue_agent_download_token(expiration_time=body.expires_at)
    return ApiResponse(
        AgentDownloadTokenObjectModel(
            id=token.token_id,
            domainType="agent_download_token",
            extensions=AgentDownloadTokenMetadata.from_internal(token),
            links=[],
        ),
        status_code=201,
    )


ENDPOINT_CREATE_AGENT_DOWNLOAD_TOKEN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=collection_href("agent_download_token"),
        link_relation="cmk/create_agent_download_token",
        method="post",
    ),
    permissions=EndpointPermissions(required=_DOWNLOAD_PERMISSIONS),
    doc=EndpointDoc(family=AGENTS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=create_agent_download_token_v1)},
)
