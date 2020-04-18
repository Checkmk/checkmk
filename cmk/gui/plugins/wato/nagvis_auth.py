#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Register general nagvis permissions"""

from cmk.gui.i18n import _
from cmk.gui.permissions import (
    permission_section_registry,
    PermissionSection,
    permission_registry,
    Permission,
)


@permission_section_registry.register
class PermissionSectionNagVis(PermissionSection):
    @property
    def name(self):
        return "nagvis"

    @property
    def title(self):
        return _('NagVis')


@permission_registry.register
class PermissionNagVisFull(Permission):
    @property
    def section(self):
        return PermissionSectionNagVis

    @property
    def permission_name(self):
        return "*_*_*"

    @property
    def title(self):
        return _('Full access')

    @property
    def description(self):
        return _('This permission grants full access to NagVis.')

    @property
    def defaults(self):
        return ["admin"]


@permission_registry.register
class PermissionNagVisRotations(Permission):
    @property
    def section(self):
        return PermissionSectionNagVis

    @property
    def permission_name(self):
        return "Rotation_view_*"

    @property
    def title(self):
        return _('Use all map rotations')

    @property
    def description(self):
        return _('Grants read access to all rotations.')

    @property
    def defaults(self):
        return ["guest"]


@permission_registry.register
class PermissionNagVisMapsViewAll(Permission):
    @property
    def section(self):
        return PermissionSectionNagVis

    @property
    def permission_name(self):
        return "Map_view_*"

    @property
    def title(self):
        return _('View all maps')

    @property
    def description(self):
        return _('Grants read access to all maps.')

    @property
    def defaults(self):
        return ["guest"]


@permission_registry.register
class PermissionNagVisMapsEditAll(Permission):
    @property
    def section(self):
        return PermissionSectionNagVis

    @property
    def permission_name(self):
        return "Map_edit_*"

    @property
    def title(self):
        return _('Edit all maps')

    @property
    def description(self):
        return _('Grants modify access to all maps.')

    @property
    def defaults(self):
        return []


@permission_registry.register
class PermissionNagVisMapsDeleteAll(Permission):
    @property
    def section(self):
        return PermissionSectionNagVis

    @property
    def permission_name(self):
        return "Map_delete_*"

    @property
    def title(self):
        return _('Delete all maps')

    @property
    def description(self):
        return _('Permits to delete all maps.')

    @property
    def defaults(self):
        return []


@permission_registry.register
class PermissionNagVisPermittedMapsView(Permission):
    @property
    def section(self):
        return PermissionSectionNagVis

    @property
    def permission_name(self):
        return "Map_view"

    @property
    def title(self):
        return _('View permitted maps')

    @property
    def description(self):
        return _('Grants read access to all maps the user is a contact for.')

    @property
    def defaults(self):
        return ['user']


@permission_registry.register
class PermissionNagVisPermittedMapsEdit(Permission):
    @property
    def section(self):
        return PermissionSectionNagVis

    @property
    def permission_name(self):
        return "Map_edit"

    @property
    def title(self):
        return _('Edit permitted maps')

    @property
    def description(self):
        return _('Grants modify access to all maps the user is contact for.')

    @property
    def defaults(self):
        return ['user']


@permission_registry.register
class PermissionNagVisPermittedMapsDelete(Permission):
    @property
    def section(self):
        return PermissionSectionNagVis

    @property
    def permission_name(self):
        return "Map_delete"

    @property
    def title(self):
        return _('Delete permitted maps')

    @property
    def description(self):
        return _('Permits to delete all maps the user is contact for.')

    @property
    def defaults(self):
        return ['user']
