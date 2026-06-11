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
from cmk.gui.openapi.restful_objects.constructors import object_href

from ._family import MASTER_CONTROL_FAMILY
from ._utils import PERMISSIONS, read_master_control_state, serialize_master_control
from .models.response_models import MasterControlModel


def show_master_control_v1(
    site_id: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_exist),
        PathParam(description="An existing site ID.", example="prod"),
    ],
) -> MasterControlModel:
    """Show the master control settings of a site"""
    user.need_permission("sidesnap.master_control")
    live = sites.live()
    return serialize_master_control(site_id, read_master_control_state(live, site_id))


ENDPOINT_SHOW_MASTER_CONTROL = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("master_control", "{site_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=MASTER_CONTROL_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=show_master_control_v1)},
    behavior=EndpointBehavior(skip_locking=True),
)
