#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.watolib.site_management import SitesApiMgr

from .endpoint_family import SITE_MANAGEMENT_FAMILY
from .models.response_models import SiteConnectionModel
from .utils import PERMISSIONS


def show_site_connection_v1(
    site_id: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_exist),
        PathParam(description="An existing site ID.", example="prod"),
    ],
) -> SiteConnectionModel:
    """Show a site connection"""
    user.need_permission("wato.sites")
    return SiteConnectionModel.from_internal(SitesApiMgr().get_a_site(site_id))


ENDPOINT_SHOW_SITE_CONNECTION = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("site_connection", "{site_id}"),
        link_relation="cmk/show",
        method="get",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=SITE_MANAGEMENT_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=show_site_connection_v1)},
)
