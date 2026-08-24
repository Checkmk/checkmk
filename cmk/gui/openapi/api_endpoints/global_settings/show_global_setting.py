#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href

from ._family import GLOBAL_SETTINGS_FAMILY
from ._utils import GlobalSettingVarName, need_read_permission, RO_PERMISSIONS
from .models.response_models import GlobalSettingModel


def show_global_setting_v1(
    api_context: ApiContext,
    varname: GlobalSettingVarName,
) -> GlobalSettingModel:
    """Show a global setting

    Also serves Event Console settings.
    """
    need_read_permission(varname)
    raise NotImplementedError("Reading global setting values is not implemented yet.")


ENDPOINT_SHOW_GLOBAL_SETTING = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("global_setting", "{varname}"),
        link_relation="cmk/show",
        method="get",
    ),
    # TODO: needs EndpointBehavior(etag="output") and an ApiResponse(etag=...).
    permissions=EndpointPermissions(required=RO_PERMISSIONS),
    doc=EndpointDoc(family=GLOBAL_SETTINGS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_global_setting_v1)},
)
