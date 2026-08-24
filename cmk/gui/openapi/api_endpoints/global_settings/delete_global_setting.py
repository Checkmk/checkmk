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
from ._utils import GlobalSettingVarName, need_write_permission, RW_PERMISSIONS


def delete_global_setting_v1(
    api_context: ApiContext,
    varname: GlobalSettingVarName,
) -> None:
    """Reset a global setting to its default value

    Also serves Event Console settings.
    """
    need_write_permission(varname)
    # TODO: an Event Console setting must scope its pending change to
    #       _get_event_console_sync_sites(), not to all activation sites.
    raise NotImplementedError("Resetting global settings is not implemented yet.")


ENDPOINT_DELETE_GLOBAL_SETTING = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("global_setting", "{varname}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    # TODO: needs EndpointBehavior(etag="input").
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=GLOBAL_SETTINGS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=delete_global_setting_v1)},
)
