#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Register general nagvis permissions"""

from cmk.gui.i18n import _, _l
from cmk.gui.permissions import (
    Permission,
    permission_registry,
    permission_section_registry,
    PermissionSection,
)


@permission_section_registry.register
class PermissionSectionNagVis(PermissionSection):
    @property
    def name(self):
        return "nagvis"

    @property
    def title(self):
        return _("NagVis")


permission_registry.register(
    Permission(
        section=PermissionSectionNagVis,
        name="*_*_*",
        title=_l("Full access"),
        description=_l("This permission grants full access to NagVis."),
        defaults=["admin"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionNagVis,
        name="Rotation_view_*",
        title=_l("Use all map rotations"),
        description=_l("Grants read access to all rotations."),
        defaults=["guest"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionNagVis,
        name="Map_view_*",
        title=_l("View all maps"),
        description=_l("Grants read access to all maps."),
        defaults=["guest"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionNagVis,
        name="Map_edit_*",
        title=_l("Edit all maps"),
        description=_l("Grants modify access to all maps."),
        defaults=[],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionNagVis,
        name="Map_delete_*",
        title=_l("Delete all maps"),
        description=_l("Permits to delete all maps."),
        defaults=[],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionNagVis,
        name="Map_view",
        title=_l("View permitted maps"),
        description=_l("Grants read access to all maps the user is a contact for."),
        defaults=["user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionNagVis,
        name="Map_edit",
        title=_l("Edit permitted maps"),
        description=_l("Grants modify access to all maps the user is contact for."),
        defaults=["user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionNagVis,
        name="Map_delete",
        title=_l("Delete permitted maps"),
        description=_l("Permits to delete all maps the user is contact for."),
        defaults=["user"],
    )
)
