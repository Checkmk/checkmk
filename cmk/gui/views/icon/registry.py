#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.plugin_registry import Registry

from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.i18n import _
from cmk.gui.permissions import declare_permission

from .base import Icon


class IconRegistry(Registry[type[Icon]]):
    def plugin_name(self, instance):
        return instance.ident()

    def registration_hook(self, instance):
        ident = self.plugin_name(instance)
        declare_permission(
            "icons_and_actions.%s" % ident,
            ident,
            _("Allow to see the icon %s in the host and service views") % ident,
            default_authorized_builtin_role_ids,
        )


icon_and_action_registry = IconRegistry()


def get_multisite_icons() -> dict[str, Icon]:
    icons = {}

    for icon_class in icon_and_action_registry.values():
        icons[icon_class.ident()] = icon_class()

    return icons
