#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.spec.utils import LIVESTATUS_GENERIC_EXPLANATION

from ._family import MASTER_CONTROL_FAMILY
from ._utils import apply_master_control_changes, PERMISSIONS
from .models.request_models import UpdateMasterControlModel


def update_master_control_v1(
    body: UpdateMasterControlModel,
    site_id: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_exist),
        PathParam(description="An existing site ID.", example="prod"),
    ],
) -> ApiResponse[None]:
    """Update the master control settings of a site

    Only the settings included in the request body are changed; the others are left untouched.
    The commands are sent to the monitoring core but, unlike the GUI snap-in, this endpoint does
    not wait for the core to apply them. Read the settings again to confirm the new state.
    """
    user.need_permission("sidesnap.master_control")
    changes = body.to_changes()
    if changes:
        apply_master_control_changes(sites.live(), site_id, changes)
    return ApiResponse(body=None, status_code=204)


ENDPOINT_UPDATE_MASTER_CONTROL = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("master_control", "{site_id}"),
        link_relation=".../update",
        method="patch",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=MASTER_CONTROL_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={
        APIVersion.V1: EndpointHandler(
            handler=update_master_control_v1,
            status_descriptions={
                204: "The master control commands have been sent to Livestatus. "
                + LIVESTATUS_GENERIC_EXPLANATION
            },
        )
    },
)
