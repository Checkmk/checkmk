#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.ccc.site import omd_site
from cmk.gui.i18n import _
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
from cmk.gui.watolib.global_settings import (
    add_global_settings_change,
    affected_sites,
    effective_value,
    global_settings_diff_text,
    load_configuration_settings,
    need_write_permission,
    save_global_settings,
)
from cmk.shared_typing.global_settings import GlobalSettingsOrigin
from cmk.web.utils.html import HTML

from ._family import GLOBAL_SETTINGS_FAMILY
from ._utils import (
    ensure_changes_allowed,
    ensure_setup_access,
    form_spec_of,
    global_setting_etag,
    global_settings_context_of,
    GlobalSettingVarName,
    make_pending_changes,
    RW_PERMISSIONS,
    value_from_json,
    value_to_json,
)
from .models.request_models import UpdateGlobalSettingModel
from .models.response_models import GlobalSettingModel


def update_global_setting_v1(
    api_context: ApiContext,
    varname: GlobalSettingVarName,
    body: UpdateGlobalSettingModel,
) -> ApiResponse[GlobalSettingModel]:
    """Update a global setting

    Also serves Event Console settings.
    """
    ensure_setup_access(api_context)
    config_variable = config_variable_registry[varname]
    need_write_permission(config_variable)
    ensure_changes_allowed(api_context)
    context = global_settings_context_of(omd_site(), api_context)
    form_spec = form_spec_of(config_variable, omd_site(), api_context)

    settings = dict(load_configuration_settings())
    old_value, old_origin = effective_value(settings, varname)
    if api_context.etag.enabled:
        api_context.etag.verify(global_setting_etag(varname, old_value, old_origin))

    new_value = value_from_json(form_spec, body.value)
    settings[varname] = new_value
    save_global_settings(settings, api_context.config.sites)

    add_global_settings_change(
        config_variable,
        text=HTML.with_escaping(
            _("Changed global configuration variable %(varname)s.") % {"varname": varname}
        ),
        sites=affected_sites(config_variable),
        pending_changes=make_pending_changes(api_context),
        diff_text=global_settings_diff_text(
            config_variable,
            context,
            {varname: old_value} if old_origin is GlobalSettingsOrigin.global_ else {},
            {varname: new_value},
        ),
    )

    json_value = value_to_json(form_spec, new_value)
    return ApiResponse(
        body=GlobalSettingModel(
            varname=varname, value=json_value, origin=GlobalSettingsOrigin.global_
        ),
        status_code=200,
        etag=global_setting_etag(varname, new_value, GlobalSettingsOrigin.global_),
    )


ENDPOINT_UPDATE_GLOBAL_SETTING = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("global_setting", "{varname}"),
        link_relation=".../update",
        method="put",
    ),
    behavior=EndpointBehavior(etag="both"),
    permissions=EndpointPermissions(required=RW_PERMISSIONS),
    doc=EndpointDoc(family=GLOBAL_SETTINGS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=update_global_setting_v1)},
)
