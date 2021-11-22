#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Hosts (internal)

WARNING: Use at your own risk, not supported.
"""

from uuid import UUID

from cmk.utils.agent_registration import UUIDLinkManager
from cmk.utils.paths import data_source_push_agent_dir, received_outputs_dir
from cmk.utils.type_defs import HostName

from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.utils import may_fail
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint, request_schemas
from cmk.gui.plugins.openapi.restful_objects.parameters import HOST_NAME
from cmk.gui.watolib.hosts_and_folders import Host


def _check_host_editing_permissions(host_name: HostName) -> None:
    Host.load_host(host_name).need_permission("write")


def _link_with_uuid(
    host_name: HostName,
    uuid: UUID,
) -> None:
    UUIDLinkManager(
        received_outputs_dir=received_outputs_dir,
        data_source_dir=data_source_push_agent_dir,
    ).create_link(
        host_name,
        uuid,
    )


@Endpoint(
    constructors.object_action_href(
        "host_config",
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
    output_empty=True,
)
def link_with_uuid(params) -> Response:
    """Link a host to a UUID"""
    with may_fail(MKAuthException):
        _check_host_editing_permissions(host_name := params["host_name"])
    _link_with_uuid(
        host_name,
        params["body"]["uuid"],
    )
    return Response(status=204)
