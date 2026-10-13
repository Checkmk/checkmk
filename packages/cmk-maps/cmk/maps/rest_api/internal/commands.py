#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The monitoring commands on a map object that Checkmk's REST API does not offer.

A thin wrapper around :func:`cmk.maps.gui._commands.run_map_command`, which
issues the command through Checkmk's own command layer (``livestatus_utils`` over
``sites.live()``) in the caller's request context. The per-verb permission and
the target's visibility are checked there.
"""

from typing import get_args

from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.maps.gui._commands import MapCommand, MapCommandVerb, run_map_command
from cmk.maps.gui._tickets import COMMAND_ACTION_PERMISSIONS
from cmk.maps.rest_api.internal.endpoint_family import MAPS_INTERNAL_FAMILY
from cmk.maps.rest_api.internal.models.request_models import MapsCommandRequest
from cmk.maps.rest_api.utils import LIVESTATUS_PERMISSIONS, NO_CONFIG_CHANGE
from cmk.web.utils import permission_verification as permissions

# The verb decides which action permission is required, so exactly one of them is.
_COMMAND_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("maps.use"),
        permissions.Perm("general.act"),
        permissions.AnyPerm(
            [
                permissions.Perm(permission)
                for permission in sorted(
                    {
                        COMMAND_ACTION_PERMISSIONS[verb]
                        for verb in get_args(MapCommandVerb.__value__)
                    }
                )
            ]
        ),
        *LIVESTATUS_PERMISSIONS,
    ]
)


def run_command_v1(body: MapsCommandRequest) -> None:
    """Run a monitoring command on a map object"""
    user.need_permission("maps.use")
    run_map_command(
        MapCommand(
            action=body.action,
            host_name=body.host_name,
            service_description=ApiOmitted.to_optional(body.service_description),
            site_id=ApiOmitted.to_optional(body.site_id),
        )
    )


ENDPOINT_RUN_COMMAND = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("maps_command", "run"),
        link_relation="cmk/run_maps_command",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=_COMMAND_PERMISSIONS),
    doc=EndpointDoc(family=MAPS_INTERNAL_FAMILY.name),
    behavior=NO_CONFIG_CHANGE,
    versions={APIVersion.INTERNAL: EndpointHandler(handler=run_command_v1)},
)
