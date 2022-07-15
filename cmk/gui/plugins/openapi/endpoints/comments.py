#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Comments

In Checkmk you can add comments to hosts and services to store textual information related to the object.
The comments can later be viewed through the user interface or read via API. You could e.g.
add maintenance information about the related host or service to help your colleagues in case problems occur.

The POST endpoints allows creating comments for both hosts and services.
Each host or service can have multiple comments.

Related documentation
    https://docs.checkmk.com/latest/en/commands.html#commands


"""

from cmk.gui import sites
from cmk.gui.http import Response
from cmk.gui.livestatus_utils.commands import comment as livestatus_comments
from cmk.gui.logged_in import user
from cmk.gui.plugins.openapi.restful_objects import constructors, Endpoint, request_schemas


@Endpoint(
    constructors.collection_href("comment", "host"),
    "cmk/create_for_host",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=request_schemas.CreateHostComment,
    output_empty=True,
    # permissions_required=PERMISSIONS,
    update_config_generation=False,
)
def create_host_comment(params):
    """Create a host comment"""
    body = params["body"]
    live_connection = sites.live()

    livestatus_comments.add_host_comment(
        connection=live_connection,
        host_name=body["host_name"],
        comment=body["comment"],
        persistent=body["persistent"],
        user=user.ident,
    )

    return Response(status=204)


@Endpoint(
    constructors.collection_href("comment", "service"),
    "cmk/create_for_service",
    method="post",
    tag_group="Monitoring",
    skip_locking=True,
    request_schema=request_schemas.CreateServiceComment,
    output_empty=True,
    # permissions_required=PERMISSIONS,
    update_config_generation=False,
)
def create_service_comment(params):
    """Create a service comment"""
    body = params["body"]
    live_connection = sites.live()

    livestatus_comments.add_service_comment(
        connection=live_connection,
        host_name=body["host_name"],
        service_description=body["service_description"],
        comment=body["comment"],
        persistent=body["persistent"],
        user=user.ident,
    )

    return Response(status=204)
