#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Hosts (internal)

WARNING: Use at your own risk, not supported.
"""

from typing import Literal
from uuid import UUID

from cmk.utils.agent_registration import get_uuid_link_manager
from cmk.utils.type_defs import HostName

from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.utils import ProblemException
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    permissions,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME
from cmk.gui.plugins.openapi.utils import serve_json
from cmk.gui.watolib.hosts_and_folders import CREHost, Host


def _check_host_access_permissions(
    host_name: HostName,
    *,
    access_type: Literal["read", "write"],
) -> CREHost:
    host = Host.load_host(host_name)
    try:
        host.need_permission(access_type)
    except MKAuthException:
        raise ProblemException(
            status=401,
            title=f"You do not have {access_type} access to the host {host_name}",
        )
    return host


def _link_with_uuid(
    host_name: HostName,
    host: CREHost,
    uuid: UUID,
) -> None:
    uuid_link_manager = get_uuid_link_manager()
    uuid_link_manager.create_link(
        host_name,
        uuid,
        create_target_dir=host.effective_attributes().get("cmk_agent_connection") == "push-agent",
    )


@Endpoint(
    constructors.object_action_href(
        "host_config_internal",
        "{host_name}",
        action_name="link_uuid",
    ),
    "cmk/link_uuid",
    method="put",
    tag_group="Checkmk Internal",
    additional_status_codes=[401],
    status_descriptions={
        401: "You do not have the permissions to edit this host.",
    },
    path_params=[HOST_NAME],
    request_schema=request_schemas.LinkHostUUID,
    permissions_required=permissions.AnyPerm(
        [
            permissions.Perm("wato.all_folders"),
            permissions.Perm("wato.edit_hosts"),
            permissions.Ignore(permissions.Perm("wato.see_all_folders")),
        ]
    ),
    output_empty=True,
)
def link_with_uuid(params) -> Response:
    """Link a host to a UUID"""
    _link_with_uuid(
        host_name := params["host_name"],
        _check_host_access_permissions(
            host_name,
            access_type="write",
        ),
        params["body"]["uuid"],
    )
    return Response(status=204)


@Endpoint(
    constructors.object_href(
        "host_config_internal",
        "{host_name}",
    ),
    "cmk/show",
    method="get",
    tag_group="Checkmk Internal",
    additional_status_codes=[401],
    status_descriptions={
        401: "You do not have read access to this host.",
    },
    path_params=[HOST_NAME],
    response_schema=response_schemas.HostConfigSchemaInternal,
    permissions_required=permissions.Optional(permissions.Perm("wato.see_all_folders")),
)
def show_host(params) -> Response:
    """Show a host"""
    host = _check_host_access_permissions(
        params["host_name"],
        access_type="read",
    )
    return serve_json(
        {
            "site": host.site_id(),
            "is_cluster": host.is_cluster(),
        }
    )
