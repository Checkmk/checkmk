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
    permission_section_registry.register(PermissionSectionNagVis)
    permission_registry.register(PermissionFullAccess)
    permission_registry.register(PermissionRotationViewAll)
    permission_registry.register(PermissionMapViewAll)
    permission_registry.register(PermissionMapEditAll)
    permission_registry.register(PermissionMapDeleteAll)
    permission_registry.register(PermissionMapView)
    permission_registry.register(PermissionMapEdit)
    permission_registry.register(PermissionMapDelete)


class PermissionSectionNagVis(PermissionSection):
    @property
    def name(self) -> str:
        return "nagvis"

    @property
    def title(self) -> str:
        return _("NagVis")


PermissionFullAccess = Permission(
    section=PermissionSectionNagVis,
    name="*_*_*",
    title=_l("Full access"),
    description=_l("This permission grants full access to NagVis."),
    defaults=["admin"],
)

PermissionRotationViewAll = Permission(
    section=PermissionSectionNagVis,
    name="Rotation_view_*",
    title=_l("Use all map rotations"),
    description=_l("Grants read access to all rotations."),
    defaults=["guest"],
)

PermissionMapViewAll = Permission(
    section=PermissionSectionNagVis,
    name="Map_view_*",
    title=_l("View all maps"),
    description=_l("Grants read access to all maps."),
    defaults=["guest"],
)

PermissionMapEditAll = Permission(
    section=PermissionSectionNagVis,
    name="Map_edit_*",
    title=_l("Edit all maps"),
    description=_l("Grants modify access to all maps."),
    defaults=[],
)

PermissionMapDeleteAll = Permission(
    section=PermissionSectionNagVis,
    name="Map_delete_*",
    title=_l("Delete all maps"),
    description=_l("Permits to delete all maps."),
    defaults=[],
)

PermissionMapView = Permission(
    section=PermissionSectionNagVis,
    name="Map_view",
    title=_l("View permitted maps"),
    description=_l("Grants read access to all maps the user is a contact for."),
    defaults=["user"],
)

PermissionMapEdit = Permission(
    section=PermissionSectionNagVis,
    name="Map_edit",
    title=_l("Edit permitted maps"),
    description=_l("Grants modify access to all maps the user is contact for."),
    defaults=["user"],
)

PermissionMapDelete = Permission(
    section=PermissionSectionNagVis,
    name="Map_delete",
    title=_l("Delete permitted maps"),
    description=_l("Permits to delete all maps the user is contact for."),
    defaults=["user"],
)
