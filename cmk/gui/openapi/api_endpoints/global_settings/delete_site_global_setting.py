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
from cmk.gui.openapi.restful_objects.constructors import sub_object_href
from cmk.gui.watolib.config_domain_name import config_variable_registry
from cmk.gui.watolib.global_settings import (
    add_global_settings_change,
    effective_site_value,
    global_settings_diff_text,
    load_configuration_settings,
    need_site_write_permission,
)
from cmk.gui.watolib.sites import load_site_globals
from cmk.shared_typing.global_settings import GlobalSettingsOrigin
from cmk.web.utils.html import HTML

from ._family import GLOBAL_SETTINGS_FAMILY
from ._utils import (
    ensure_changes_allowed,
    ensure_setup_access,
    global_settings_context_of,
    GlobalSettingVarName,
    load_configured_sites,
    make_pending_changes,
    save_site_setting,
    site_global_setting_etag,
    SITE_RW_PERMISSIONS,
    SiteIdPathParam,
)


def delete_site_global_setting_v1(
    api_context: ApiContext,
    site_id: SiteIdPathParam,
    varname: GlobalSettingVarName,
) -> None:
    """Remove a site-specific global setting

    Also serves Event Console settings.
    """
    ensure_setup_access(api_context)
    config_variable = config_variable_registry[varname]
    need_site_write_permission(config_variable)
    ensure_changes_allowed(api_context)

    sites = load_configured_sites()
    site_globals = load_site_globals(sites, site_id)
    old_value, old_origin = effective_site_value(
        site_globals, varname, global_settings=load_configuration_settings()
    )
    if api_context.etag.enabled:
        api_context.etag.verify(site_global_setting_etag(site_id, varname, old_value, old_origin))

    if old_origin is not GlobalSettingsOrigin.site:
        # There is no override to remove, so DELETE stays idempotent and records no change.
        return

    del site_globals[varname]
    save_site_setting(site_id, sites, site_globals, api_context)

    add_global_settings_change(
        config_variable,
        text=HTML.with_escaping(
            _("Removed site-specific configuration variable %(varname)s for site %(site_id)s.")
            % {"varname": varname, "site_id": site_id}
        ),
        sites=[site_id],
        pending_changes=make_pending_changes(api_context),
        diff_text=global_settings_diff_text(
            config_variable,
            global_settings_context_of(site_id, api_context),
            {varname: old_value},
            {},
        ),
    )


ENDPOINT_DELETE_SITE_GLOBAL_SETTING = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=sub_object_href("global_setting", "{varname}", "site_connection", "{site_id}"),
        link_relation="cmk/delete_site_global_setting",
        method="delete",
        content_type=None,
    ),
    behavior=EndpointBehavior(etag="input"),
    permissions=EndpointPermissions(required=SITE_RW_PERMISSIONS),
    doc=EndpointDoc(family=GLOBAL_SETTINGS_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=delete_site_global_setting_v1)},
)
