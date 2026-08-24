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
from ._utils import GlobalSettingVarName, SITE_RW_PERMISSIONS, SiteIdPathParam


def delete_site_global_setting_v1(
    api_context: ApiContext,
    site_id: SiteIdPathParam,
    varname: GlobalSettingVarName,
) -> None:
    """Remove a site-specific global setting

    Also serves Event Console settings.
    """
    user.need_permission("wato.edit")
    user.need_permission("wato.global")
    user.need_permission("wato.sites")
    raise NotImplementedError("Removing site-specific global settings is not implemented yet.")


ENDPOINT_DELETE_SITE_GLOBAL_SETTING = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=sub_object_href("global_setting", "{varname}", "site_connection", "{site_id}"),
        link_relation="cmk/delete_site_global_setting",
        method="delete",
        content_type=None,
    ),
    # TODO: needs EndpointBehavior(etag="input").
    permissions=EndpointPermissions(required=SITE_RW_PERMISSIONS),
    doc=EndpointDoc(family=GLOBAL_SETTINGS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=delete_site_global_setting_v1)},
)
