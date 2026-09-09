#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from typing import Annotated

from pydantic import AfterValidator

from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.version import edition
from cmk.gui.form_specs import get_visitor, RawDiskData, RawFrontendData, VisitorOptions
from cmk.gui.global_config import get_global_config
from cmk.gui.openapi.framework import ApiContext, ETag, PathParam
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.user_sites import activation_sites, get_event_console_site_choices
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_registry,
    ConfigVariable,
    EVENT_CONSOLE,
    GlobalSettingsContext,
)
from cmk.gui.watolib.global_settings import (
    is_available_in_global_settings,
    load_configuration_settings,
    make_global_settings_context,
    save_site_global_settings,
)
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.sidebar_reload import sidebar_reload_change_hook
from cmk.gui.watolib.sites import site_globals_editable, site_management_registry
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.utils import paths
from cmk.web.utils import permission_verification as permissions

_VARIABLE_PERMISSIONS = permissions.DynamicRuntimePerm(
    description="The permissions required depend on the targeted variable"
)

RO_PERMISSIONS = _VARIABLE_PERMISSIONS
RW_PERMISSIONS = permissions.AllPerm([permissions.Perm("wato.edit"), _VARIABLE_PERMISSIONS])

SITE_RO_PERMISSIONS = permissions.AllPerm([permissions.Perm("wato.sites"), _VARIABLE_PERMISSIONS])
SITE_RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.sites"),
        _VARIABLE_PERMISSIONS,
    ]
)


def _editable_global_setting(varname: str) -> str:
    """Accepts any variable the global settings can edit, on whichever page.

    A variable the edition deactivates is rejected here; save_global_settings() would
    otherwise drop the write and the endpoint would report a success that changed nothing.
    """
    try:
        config_variable = config_variable_registry[varname]
    except KeyError:
        raise ValueError(f"Unknown configuration variable: {varname!r}.") from None

    if not is_available_in_global_settings(
        config_variable,
        default_values=ABCConfigDomain.get_all_default_globals(),
        is_activated=get_global_config().global_settings.is_activated,
    ):
        raise ValueError(
            f"The configuration variable {varname!r} is not available in the global settings."
        )

    return varname


def affected_sites(config_variable: ConfigVariable) -> list[SiteId] | None:
    """The sites a change has to be activated on; None means all activation sites."""
    if config_variable.primary_domain().ident() == EVENT_CONSOLE:
        return [site_id for site_id, _title in get_event_console_site_choices()]

    return None


def _site_globals_editable(value: str) -> SiteId:
    """On a non-distributed setup this only accepts sites that already carry overrides,
    which nothing can create. Same as ModeEditSiteGlobals."""
    site_id = SiteIdConverter.should_be_configurable(value)
    all_sites = load_configured_sites()
    if site_id not in all_sites or not site_globals_editable(all_sites, all_sites[site_id]):
        raise ValueError(f"Site-specific global settings cannot be edited for site {site_id!r}.")

    return site_id


SiteIdPathParam = Annotated[
    SiteId,
    TypedPlainValidator(str, _site_globals_editable),
    PathParam(description="An existing site ID.", example="prod"),
]

GlobalSettingVarName = Annotated[
    str,
    AfterValidator(_editable_global_setting),
    PathParam(
        description="The name of a global setting. Event Console settings are addressed "
        "the same way, e.g. `log_level`.",
        example="log_levels",
    ),
]


def global_settings_context_of(site_id: SiteId, api_context: ApiContext) -> GlobalSettingsContext:
    return make_global_settings_context(
        edition(paths.omd_root),
        site_id,
        sites=api_context.config.sites,
        graph_timeranges=api_context.config.graph_timeranges,
    )


def form_spec_of(
    config_variable: ConfigVariable, site_id: SiteId, api_context: ApiContext
) -> FormSpec[object]:
    return config_variable.value_model(global_settings_context_of(site_id, api_context))


def value_to_json(form_spec: FormSpec[object], value: object) -> object:
    """The frontend representation, i.e. the one the GUI exchanges with the form spec."""
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))
    _component, json_value = visitor.to_vue(RawDiskData(value))
    return json_value


def value_from_json(form_spec: FormSpec[object], json_value: object) -> object:
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=False, mask_values=False))
    if problems := visitor.validate(RawFrontendData(json_value)):
        raise ProblemException(
            status=400,
            title=f"Problem in field {'.'.join(problems[0].location)}",
            detail=problems[0].message,
        )

    return visitor.to_disk(RawFrontendData(json_value))


def _etag_value(json_value: object) -> str:
    """Not hash_of_dict(): that assumes string dict keys and repr()s in insertion order."""
    return json.dumps(json_value, sort_keys=True, default=repr)


def global_setting_etag(varname: str, json_value: object, is_default: bool) -> ETag:
    # Must cover is_default too, so that "unset -> explicitly set to the default" changes the tag.
    return ETag(
        {
            "varname": varname,
            "value": _etag_value(json_value),
            "is_default": is_default,
        }
    )


def site_global_setting_etag(
    site_id: SiteId, varname: str, json_value: object, is_default: bool
) -> ETag:
    return ETag(
        {
            "site_id": site_id,
            "varname": varname,
            "value": _etag_value(json_value),
            "is_default": is_default,
        }
    )


def effective_value(settings: Mapping[str, object], varname: str) -> tuple[object, bool]:
    """The value in effect and whether it is the built-in default.

    Writers pass the same mapping they later hand to save_global_settings(), which
    rewrites the whole file, so they need a mutable copy of it.
    """
    if varname in settings:
        return settings[varname], False

    return ABCConfigDomain.get_all_default_globals()[varname], True


def load_configured_sites() -> SiteConfigurations:
    return site_management_registry["site_management"].load_sites()


def load_site_globals(sites: SiteConfigurations, site_id: SiteId) -> dict[str, object]:
    """The site's own overrides, as a copy that writers may mutate before saving."""
    return dict(sites[site_id].get("globals", {}))


def effective_site_value(site_globals: Mapping[str, object], varname: str) -> tuple[object, bool]:
    """The value in effect for the site and whether it comes from outside the site.

    Without an override the site inherits the central value, which in turn falls back
    to the built-in default.
    """
    if varname in site_globals:
        return site_globals[varname], False

    value, _is_built_in_default = effective_value(load_configuration_settings(), varname)
    return value, True


def save_site_setting(
    site_id: SiteId,
    configured_sites: SiteConfigurations,
    site_globals: dict[str, object],
    api_context: ApiContext,
) -> None:
    configured_sites[site_id]["globals"] = site_globals
    site_management_registry["site_management"].save_sites(
        make_folder_tree(api_context.config),
        configured_sites,
        activate=False,
        pprint_value=api_context.config.wato_pprint_config,
        liveproxyd_enabled=api_context.config.liveproxyd_enabled,
        use_git=api_context.config.wato_use_git,
        acting_user_id=api_context.user.id,
    )
    if site_id == omd_site():
        save_site_global_settings(site_globals)


def make_pending_changes(api_context: ApiContext) -> PendingChanges:
    return PendingChanges(
        activation_sites=activation_sites(api_context.config.sites),
        local_site=omd_site(),
        acting_user=api_context.user.id,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=api_context.config.wato_use_git),
            sidebar_reload_change_hook,
            index_update_change_hook,
        ),
    )
