#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.ccc.site import omd_site
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model.response import ApiResponse
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.watolib.config_domain_name import config_variable_registry
from cmk.gui.watolib.global_settings import load_configuration_settings

from ._family import GLOBAL_SETTINGS_FAMILY
from ._utils import (
    effective_value,
    form_spec_of,
    global_setting_etag,
    GlobalSettingVarName,
    need_read_permission,
    RO_PERMISSIONS,
    value_to_json,
)
from .models.response_models import GlobalSettingModel


def show_global_setting_v1(
    api_context: ApiContext,
    varname: GlobalSettingVarName,
) -> ApiResponse[GlobalSettingModel]:
    """Show a global setting

    Also serves Event Console settings.
    """
    need_read_permission(varname)
    config_variable = config_variable_registry[varname]
    value, is_default = effective_value(load_configuration_settings(), varname)
    json_value = value_to_json(form_spec_of(config_variable, omd_site(), api_context), value)
    return ApiResponse(
        body=GlobalSettingModel(varname=varname, value=json_value, is_default=is_default),
        status_code=200,
        etag=global_setting_etag(varname, json_value, is_default),
    )


ENDPOINT_SHOW_GLOBAL_SETTING = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("global_setting", "{varname}"),
        link_relation="cmk/show",
        method="get",
    ),
    behavior=EndpointBehavior(etag="output"),
    permissions=EndpointPermissions(required=RO_PERMISSIONS),
    doc=EndpointDoc(family=GLOBAL_SETTINGS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_global_setting_v1)},
)
