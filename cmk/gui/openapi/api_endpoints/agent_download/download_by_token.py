#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from cmk.gui.http import ContentDispositionType, Response
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    QueryParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.shared_endpoint_families.agent import AGENTS_FAMILY
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import AgentDownloadToken, get_token_store
from cmk.gui.utils import agent

_OS_TYPES_AVAILABLE = ["linux_deb", "linux_rpm", "windows_msi"]


def download_agent_by_token(
    api_context: ApiContext,
    os_type: Annotated[
        Literal["linux_deb", "linux_rpm", "windows_msi"],
        QueryParam(
            description=(
                "The type of the operating system. May be one of " + ", ".join(_OS_TYPES_AVAILABLE)
            ),
            example="linux_deb",
        ),
    ],
) -> Response:
    """Download the Checkmk agent via a one-time download token."""
    if not api_context.token:
        raise ProblemException(
            status=401,
            title="Authentication required",
            detail="This endpoint requires token authentication.",
        )
    if not isinstance(api_context.token.details, AgentDownloadToken):
        raise ProblemException(
            status=401,
            title="Authentication required",
            detail="Incorrect token provided. Please provide an agent download token.",
        )

    get_token_store().delete(api_context.token.token_id)

    response = Response()
    if os_type == "windows_msi":
        agent_path = agent.packed_agent_path_windows_msi()
        response.set_content_type("application/x-msi")
    elif os_type == "linux_rpm":
        agent_path = agent.packed_agent_path_linux_rpm()
        response.set_content_type("application/x-rpm")
    elif os_type == "linux_deb":
        agent_path = agent.packed_agent_path_linux_deb()
        response.set_content_type("application/x-deb")
    else:
        raise AssertionError(f"Agent: os_type '{os_type}' not known in this edition.")

    response.set_content_disposition(ContentDispositionType.ATTACHMENT, agent_path.name)
    with open(agent_path, mode="rb") as f:
        response.data = f.read()
    response.status_code = 200
    return response


ENDPOINT_DOWNLOAD_BY_TOKEN = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("agent", "download_by_token"),
        link_relation="cmk/download_by_token",
        method="get",
        content_type="application/octet-stream",
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=AGENTS_FAMILY.name, group="Checkmk Internal"),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=download_agent_by_token)},
    allowed_tokens={"agent_download"},
)
