#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
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
from cmk.gui.openapi.restful_objects.constructors import sub_object_href
from cmk.gui.watolib.config_domain_name import config_variable_registry
from cmk.gui.watolib.global_settings import add_global_settings_change, global_settings_diff_text
from cmk.web.utils.html import HTML

from ._family import GLOBAL_SETTINGS_FAMILY
from ._utils import (
    effective_site_value,
    form_spec_of,
    global_settings_context_of,
    GlobalSettingVarName,
    load_configured_sites,
    load_site_globals,
    make_pending_changes,
    need_site_write_permission,
    save_site_setting,
    site_global_setting_etag,
    SITE_RW_PERMISSIONS,
    SiteIdPathParam,
    value_from_json,
    value_to_json,
)
from .models.request_models import UpdateGlobalSettingModel
from .models.response_models import SiteGlobalSettingModel


def update_site_global_setting_v1(
    api_context: ApiContext,
    site_id: SiteIdPathParam,
    varname: GlobalSettingVarName,
    body: UpdateGlobalSettingModel,
) -> ApiResponse[SiteGlobalSettingModel]:
    """Update a site-specific global setting

    Also serves Event Console settings.
    """
    need_site_write_permission(varname)
    config_variable = config_variable_registry[varname]
    form_spec = form_spec_of(config_variable, site_id, api_context)

    sites = load_configured_sites()
    site_globals = load_site_globals(sites, site_id)
    old_value, was_default = effective_site_value(site_globals, varname)
    if api_context.etag.enabled:
        api_context.etag.verify(
            site_global_setting_etag(
                site_id, varname, value_to_json(form_spec, old_value), was_default
            )
        )

    new_value = value_from_json(form_spec, body.value)
    site_globals[varname] = new_value
    save_site_setting(site_id, sites, site_globals, api_context)

    add_global_settings_change(
        config_variable,
        text=HTML.with_escaping(
            _("Changed site-specific configuration variable %(varname)s for site %(site_id)s.")
            % {"varname": varname, "site_id": site_id}
        ),
        sites=[site_id],
        pending_changes=make_pending_changes(api_context),
        diff_text=global_settings_diff_text(
            config_variable,
            global_settings_context_of(site_id, api_context),
            {} if was_default else {varname: old_value},
            {varname: new_value},
        ),
    )

    # The site now carries an override, so the value no longer comes from outside it.
    json_value = value_to_json(form_spec, new_value)
    return ApiResponse(
        body=SiteGlobalSettingModel(
            site_id=site_id, varname=varname, value=json_value, is_default=False
        ),
        status_code=200,
        etag=site_global_setting_etag(site_id, varname, json_value, False),
    )


ENDPOINT_UPDATE_SITE_GLOBAL_SETTING = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=sub_object_href("global_setting", "{varname}", "site_connection", "{site_id}"),
        link_relation="cmk/update_site_global_setting",
        method="put",
    ),
    behavior=EndpointBehavior(etag="both"),
    permissions=EndpointPermissions(required=SITE_RW_PERMISSIONS),
    doc=EndpointDoc(family=GLOBAL_SETTINGS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=update_site_global_setting_v1)},
)
