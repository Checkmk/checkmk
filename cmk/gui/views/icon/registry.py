#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.plugin_registry import Registry

from cmk.gui.config import active_config, default_authorized_builtin_role_ids
from cmk.gui.i18n import _
from cmk.gui.permissions import declare_permission

from .base import Icon
from .config_icons import config_based_icons, update_builtin_icons_from_config


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


def all_icons() -> dict[str, Icon]:
    return update_builtin_icons_from_config(
        {ident: cls() for ident, cls in icon_and_action_registry.items()},
        active_config.builtin_icon_visibility,
    ) | config_based_icons(active_config.user_icons_and_actions)
