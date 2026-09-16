#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Annotated

from pydantic import AfterValidator

from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.version import edition
from cmk.gui.form_specs import get_visitor, RawDiskData, RawFrontendData, VisitorOptions
from cmk.gui.global_config import get_global_config
from cmk.gui.openapi.framework import ApiContext, ETag, PathParam
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.user_sites import activation_sites
from cmk.gui.watolib import read_only
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_registry,
    ConfigVariable,
    GlobalSettingsContext,
)
from cmk.gui.watolib.global_settings import (
    is_available_in_global_settings,
    make_global_settings_context,
)
from cmk.gui.watolib.global_settings import (
    make_pending_changes as make_setup_pending_changes,
)
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.pending_changes import PendingChanges
from cmk.gui.watolib.sites import (
    save_site_globals,
    site_globals_editable,
    site_management_registry,
)
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing.global_settings import GlobalSettingsOrigin
from cmk.utils import paths
from cmk.web.utils import permission_verification as permissions
from cmk.web.utils.escaping import strip_tags

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

    A variable the edition deactivates is rejected here; the settings writer would
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


def _site_globals_editable(value: str) -> SiteId:
    """On a non-distributed setup this only accepts sites that already carry overrides,
    which nothing can create."""
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


def ensure_setup_access(api_context: ApiContext) -> None:
    if not api_context.config.wato_enabled:
        raise ProblemException(
            status=403,
            title="Setup is disabled",
            detail="This endpoint is currently disabled via the "
            "'Disable remote configuration' option in 'Distributed Monitoring'. "
            "You may be able to query the central site.",
        )
    if not api_context.config.is_provider_site:
        raise ProblemException(
            status=403,
            title="Not the central site of the provider",
            detail="Checkmk can only be configured on the managers central site.",
        )


def ensure_changes_allowed(api_context: ApiContext) -> None:
    if read_only.blocks_changes(api_context.config.wato_read_only):
        raise ProblemException(
            status=403,
            title="Setup is in read-only mode",
            detail=strip_tags(read_only.message(api_context.config.wato_read_only)),
        )


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


def _etag_value(value: object) -> str:
    """Not hash_of_dict(): that assumes string dict keys and repr()s in insertion order."""
    return json.dumps(value, sort_keys=True, default=repr)


def global_setting_etag(varname: str, value: object, origin: GlobalSettingsOrigin) -> ETag:
    # Must cover the origin too, so that "unset -> explicitly set to the default" changes the tag.
    return ETag(
        {
            "varname": varname,
            "value": _etag_value(value),
            "origin": origin.value,
        }
    )


def site_global_setting_etag(
    site_id: SiteId, varname: str, value: object, origin: GlobalSettingsOrigin
) -> ETag:
    return ETag(
        {
            "site_id": site_id,
            "varname": varname,
            "value": _etag_value(value),
            "origin": origin.value,
        }
    )


def load_configured_sites() -> SiteConfigurations:
    return site_management_registry["site_management"].load_sites()


def save_site_setting(
    site_id: SiteId,
    configured_sites: SiteConfigurations,
    site_globals: dict[str, object],
    api_context: ApiContext,
) -> None:
    save_site_globals(
        site_id,
        configured_sites,
        site_globals,
        tree=make_folder_tree(api_context.config),
        pprint_value=api_context.config.wato_pprint_config,
        liveproxyd_enabled=api_context.config.liveproxyd_enabled,
        use_git=api_context.config.wato_use_git,
        acting_user_id=api_context.user.id,
    )


def make_pending_changes(api_context: ApiContext) -> PendingChanges:
    return make_setup_pending_changes(
        activation_sites=activation_sites(api_context.config.sites),
        local_site=omd_site(),
        acting_user=api_context.user.id,
        use_git=api_context.config.wato_use_git,
    )
