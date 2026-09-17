#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
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
from cmk.gui.openapi.restful_objects.constructors import sub_object_href
from cmk.gui.watolib.config_domain_name import config_variable_registry
from cmk.gui.watolib.global_settings import (
    effective_site_value,
    load_configuration_settings,
    need_site_read_permission,
)
from cmk.gui.watolib.sites import load_site_globals

from ._family import GLOBAL_SETTINGS_FAMILY
from ._utils import (
    ensure_setup_access,
    form_spec_of,
    GlobalSettingVarName,
    load_configured_sites,
    site_global_setting_etag,
    SITE_RO_PERMISSIONS,
    SiteIdPathParam,
    value_to_json,
)
from .models.response_models import SiteGlobalSettingModel


def show_site_global_setting_v1(
    api_context: ApiContext,
    site_id: SiteIdPathParam,
    varname: GlobalSettingVarName,
) -> ApiResponse[SiteGlobalSettingModel]:
    """Show a site-specific global setting

    Also serves Event Console settings.
    """
    ensure_setup_access(api_context)
    config_variable = config_variable_registry[varname]
    need_site_read_permission(config_variable)
    sites = load_configured_sites()
    value, origin = effective_site_value(
        load_site_globals(sites, site_id),
        varname,
        global_settings=load_configuration_settings(),
    )
    json_value = value_to_json(form_spec_of(config_variable, site_id, api_context), value)
    return ApiResponse(
        body=SiteGlobalSettingModel(
            site_id=site_id, varname=varname, value=json_value, origin=origin
        ),
        status_code=200,
        etag=site_global_setting_etag(site_id, varname, value, origin),
    )


ENDPOINT_SHOW_SITE_GLOBAL_SETTING = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=sub_object_href("global_setting", "{varname}", "site_connection", "{site_id}"),
        link_relation="cmk/show_site_global_setting",
        method="get",
    ),
    behavior=EndpointBehavior(etag="output"),
    permissions=EndpointPermissions(required=SITE_RO_PERMISSIONS),
    doc=EndpointDoc(family=GLOBAL_SETTINGS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=show_site_global_setting_v1)},
)
