#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from typing import Annotated

from pydantic import AfterValidator

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId
from cmk.ccc.version import edition
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import ApiContext, ETag, PathParam
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_registry,
    ConfigVariable,
    GlobalSettingsContext,
)
from cmk.gui.watolib.global_settings import make_global_settings_context
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.utils import paths
from cmk.web.utils import permission_verification as permissions

# Every value ABCConfigDomain.global_settings_permission can take, since a permission checked
# during a request must be declared. Not derivable from config_domain_registry, which is
# populated only after this module is imported.
RO_PERMISSIONS = permissions.AnyPerm(
    [
        permissions.AllPerm(
            [
                permissions.Perm("wato.global"),
                # the password visitor checks this for every secret carrying variable
                permissions.Optional(permissions.Perm("wato.edit_all_passwords")),
            ]
        ),
        permissions.Perm("mkeventd.config"),
    ]
)
RW_PERMISSIONS = permissions.AnyPerm(
    [
        permissions.AllPerm(
            [
                permissions.Perm("wato.edit"),
                permissions.Perm("wato.global"),
                # the password visitor checks this for every secret carrying variable
                permissions.Optional(permissions.Perm("wato.edit_all_passwords")),
            ]
        ),
        permissions.AllPerm(
            [
                permissions.Perm("wato.edit"),
                permissions.Perm("mkeventd.config"),
            ]
        ),
    ]
)

SITE_RO_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.global"),
        permissions.Perm("wato.sites"),
    ]
)
SITE_RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.global"),
        permissions.Perm("wato.sites"),
    ]
)


class GlobalSettingConverter:
    @staticmethod
    def _lookup(varname: str) -> ConfigVariable:
        try:
            config_variable = config_variable_registry[varname]
        except KeyError:
            raise ValueError(f"Unknown configuration variable: {varname!r}.") from None

        try:
            domain = config_variable.primary_domain()
        except KeyError:
            raise ValueError(
                f"The configuration variable {varname!r} is not available in this edition."
            ) from None

        if not domain.enabled():
            raise ValueError(
                f"The configuration variable {varname!r} belongs to a component that is "
                f"disabled on this site."
            )

        return config_variable

    @staticmethod
    def exists(varname: str) -> str:
        """Accept any variable the global settings can edit, on whichever page.

        Consults the variable's flag, not the domain's same-named one: that only says
        whether a domain shows on the default page, which the Event Console clears even
        though its variables are editable on their own page.
        """
        config_variable = GlobalSettingConverter._lookup(varname)
        if config_variable.in_global_settings():
            return varname

        raise ValueError(
            f"The configuration variable {varname!r} is not editable via global settings."
        )


def _permission_for_varname(varname: str) -> str:
    return config_variable_registry[varname].primary_domain().global_settings_permission


def need_read_permission(varname: str) -> None:
    """Must stay in sync with RO_PERMISSIONS."""
    user.need_permission(_permission_for_varname(varname))


def need_write_permission(varname: str) -> None:
    """Must stay in sync with RW_PERMISSIONS."""
    user.need_permission("wato.edit")
    user.need_permission(_permission_for_varname(varname))


# TODO: the GUI's site_globals_editable() also allows any site that already carries
#       overrides. Resolve once values are really read and written.
SiteIdPathParam = Annotated[
    SiteId,
    TypedPlainValidator(str, SiteIdConverter.should_be_configurable),
    PathParam(description="An existing site ID.", example="prod"),
]

GlobalSettingVarName = Annotated[
    str,
    AfterValidator(GlobalSettingConverter.exists),
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
    value_model = config_variable.value_model(global_settings_context_of(site_id, api_context))
    if not isinstance(value_model, FormSpec):
        raise MKGeneralException(
            f"Configuration variable {config_variable.ident()!r} is not form spec backed yet "
            f"and cannot be served by the REST API."
        )

    return value_model


def value_to_json(form_spec: FormSpec[object], value: object) -> object:
    """The frontend representation, i.e. the one the GUI exchanges with the form spec."""
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))
    _component, json_value = visitor.to_vue(RawDiskData(value))
    return json_value


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
