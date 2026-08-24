#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
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
from cmk.gui.openapi.restful_objects.constructors import sub_object_href

from ._family import GLOBAL_SETTINGS_FAMILY
from ._utils import GlobalSettingVarName, SITE_RO_PERMISSIONS, SiteIdPathParam
from .models.response_models import SiteGlobalSettingModel


def show_site_global_setting_v1(
    api_context: ApiContext,
    site_id: SiteIdPathParam,
    varname: GlobalSettingVarName,
) -> SiteGlobalSettingModel:
    """Show a site-specific global setting

    Also serves Event Console settings.
    """
    user.need_permission("wato.global")
    user.need_permission("wato.sites")
    raise NotImplementedError("Reading site-specific global setting values is not implemented yet.")


ENDPOINT_SHOW_SITE_GLOBAL_SETTING = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=sub_object_href("global_setting", "{varname}", "site_connection", "{site_id}"),
        link_relation="cmk/show_site_global_setting",
        method="get",
    ),
    # TODO: needs EndpointBehavior(etag="output") and an ApiResponse(etag=...).
    permissions=EndpointPermissions(required=SITE_RO_PERMISSIONS),
    doc=EndpointDoc(family=GLOBAL_SETTINGS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_site_global_setting_v1)},
)
