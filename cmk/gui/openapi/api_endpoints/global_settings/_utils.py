#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from pydantic import AfterValidator

from cmk.ccc.site import SiteId
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import ETag, PathParam
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.watolib.config_domain_name import config_variable_registry, ConfigVariable
from cmk.web.utils import permission_verification as permissions

# Every value ABCConfigDomain.global_settings_permission can take, since a permission checked
# during a request must be declared. Not derivable from config_domain_registry, which is
# populated only after this module is imported.
RO_PERMISSIONS = permissions.AnyPerm(
    [
        permissions.Perm("wato.global"),
        permissions.Perm("mkeventd.config"),
    ]
)
RW_PERMISSIONS = permissions.AnyPerm(
    [
        permissions.AllPerm(
            [
                permissions.Perm("wato.edit"),
                permissions.Perm("wato.global"),
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


def global_setting_etag(varname: str, value: object, is_default: bool) -> ETag:
    # Must cover is_default too, so that "unset -> explicitly set to the default" changes the tag.
    raise NotImplementedError("ETag support for global settings is not implemented yet.")


def site_global_setting_etag(
    site_id: SiteId, varname: str, value: object, is_default: bool
) -> ETag:
    raise NotImplementedError("ETag support for global settings is not implemented yet.")
