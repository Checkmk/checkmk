#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Permission section + permissions for Checkmk Maps."""

from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.i18n import _, _l
from cmk.gui.permissions import (
    Permission,
    PermissionRegistry,
    PermissionSection,
    PermissionSectionRegistry,
)

PERMISSION_SECTION_MAPS = PermissionSection(name="maps", title=_("Checkmk Maps"))

# The per-map permission section ("map", holding ``map.<name>`` for published and
# built-in maps) is declared by ``MapPage.declare_overriding_permissions()``, so
# it must NOT be registered here as well.

PermissionUse = Permission(
    section=PERMISSION_SECTION_MAPS,
    name="use",
    title=_l("Use Checkmk Maps"),
    description=_l(
        "Allows the user to open Checkmk Maps and view the maps they are permitted to see. "
        'Creating and customizing maps is granted separately (see "Customize and use maps").'
    ),
    # Same default roles that may see other users' maps, so anyone the
    # publish/permission model lets view a map can also open the application.
    defaults=list(default_authorized_builtin_role_ids),
)

PermissionConfigure = Permission(
    section=PERMISSION_SECTION_MAPS,
    name="configure",
    title=_l("Configure Checkmk Maps"),
    description=_l(
        "Grants access to the Maps administration: monitoring connections and their "
        "connection details, the shared image library and the Maps-wide configuration. "
        "Background images of a map are not covered - those belong to whoever may edit "
        "that map."
    ),
    defaults=["admin"],
)


def register(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
) -> None:
    permission_section_registry.register(PERMISSION_SECTION_MAPS)
    permission_registry.register(PermissionUse)
    permission_registry.register(PermissionConfigure)
