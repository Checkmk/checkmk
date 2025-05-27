#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Register general nagvis permissions"""

from cmk.gui.i18n import _, _l
from cmk.gui.permissions import (
    Permission,
    PermissionRegistry,
    PermissionSection,
    PermissionSectionRegistry,
)


def register(
    permission_section_registry: PermissionSectionRegistry, permission_registry: PermissionRegistry
) -> None:
    permission_section_registry.register(PERMISSION_SECTION_NAGVIS)
    permission_registry.register(PermissionFullAccess)
    permission_registry.register(PermissionRotationViewAll)
    permission_registry.register(PermissionMapViewAll)
    permission_registry.register(PermissionMapEditAll)
    permission_registry.register(PermissionMapDeleteAll)
    permission_registry.register(PermissionMapView)
    permission_registry.register(PermissionMapEdit)
    permission_registry.register(PermissionMapDelete)
    permission_registry.register(PermissionMapHTML)


PERMISSION_SECTION_NAGVIS = PermissionSection(
    name="nagvis",
    title=_("NagVis"),
)


PermissionFullAccess = Permission(
    section=PERMISSION_SECTION_NAGVIS,
    name="*_*_*",
    title=_l("Full access"),
    description=_l("This permission grants full access to NagVis."),
    defaults=["admin"],
)

PermissionRotationViewAll = Permission(
    section=PERMISSION_SECTION_NAGVIS,
    name="Rotation_view_*",
    title=_l("Use all map rotations"),
    description=_l("Grants read access to all rotations."),
    defaults=["guest"],
)

PermissionMapViewAll = Permission(
    section=PERMISSION_SECTION_NAGVIS,
    name="Map_view_*",
    title=_l("View all maps"),
    description=_l("Grants read access to all maps."),
    defaults=["guest"],
)

PermissionMapEditAll = Permission(
    section=PERMISSION_SECTION_NAGVIS,
    name="Map_edit_*",
    title=_l("Edit all maps"),
    description=_l("Grants modify access to all maps."),
    defaults=[],
)

PermissionMapDeleteAll = Permission(
    section=PERMISSION_SECTION_NAGVIS,
    name="Map_delete_*",
    title=_l("Delete all maps"),
    description=_l("Permits to delete all maps."),
    defaults=[],
)

PermissionMapView = Permission(
    section=PERMISSION_SECTION_NAGVIS,
    name="Map_view",
    title=_l("View permitted maps"),
    description=_l("Grants read access to all maps the user is a contact for."),
    defaults=["user"],
)

PermissionMapEdit = Permission(
    section=PERMISSION_SECTION_NAGVIS,
    name="Map_edit",
    title=_l("Edit permitted maps"),
    description=_l("Grants modify access to all maps the user is contact for."),
    defaults=["user"],
)

PermissionMapDelete = Permission(
    section=PERMISSION_SECTION_NAGVIS,
    name="Map_delete",
    title=_l("Delete permitted maps"),
    description=_l("Permits to delete all maps the user is contact for."),
    defaults=["user"],
)


PermissionMapHTML = Permission(
    section=PERMISSION_SECTION_NAGVIS,
    name="Map_editHtml_*",
    title=_l("Allow to add or edit elements that contain HTML"),
    description=_l(
        "Grants the access to add or edit elements that contain HTML. "
        "Enabling this for other users except admins is considered a security risk. "
    ),
    defaults=["admin"],
)
