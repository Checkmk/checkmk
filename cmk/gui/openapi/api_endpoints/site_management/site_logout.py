#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import ApiContext, PathParam
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model.converter import (
    SiteIdConverter,
    TypedPlainValidator,
)
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.watolib.site_management import SitesApiMgr

from .endpoint_family import SITE_MANAGEMENT_FAMILY
from .utils import PERMISSIONS


def site_connection_logout_v1(
    api_context: ApiContext,
    site_id: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_exist),
        PathParam(description="An existing site ID.", example="prod"),
    ],
) -> None:
    """Logout from a remote site"""
    user.need_permission("wato.sites")
    SitesApiMgr().logout_of_site(
        site_id=site_id,
        pprint_value=api_context.config.wato_pprint_config,
    )


ENDPOINT_SITE_CONNECTION_LOGOUT = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("site_connection", "{site_id}", "logout"),
        link_relation="cmk/site_logout",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=SITE_MANAGEMENT_FAMILY.name),
    versions={APIVersion.V1: EndpointHandler(handler=site_connection_logout_v1)},
)
