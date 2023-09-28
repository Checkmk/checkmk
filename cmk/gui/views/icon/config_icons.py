#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config

from .base import Icon
from .registry import icon_and_action_registry


def update_icons_from_configuration() -> None:
    _update_builtin_icons(active_config.builtin_icon_visibility)
    _register_custom_user_icons_and_actions(active_config.user_icons_and_actions)


def _update_builtin_icons(builtin_icon_visibility):
    # Now apply the global settings customized options
    for icon_id, cfg in builtin_icon_visibility.items():
        icon = icon_and_action_registry.get(icon_id)
        if icon is None:
            continue

        if "toplevel" in cfg:
            icon.override_toplevel(cfg["toplevel"])
        if "sort_index" in cfg:
            icon.override_sort_index(cfg["sort_index"])


def _register_custom_user_icons_and_actions(user_icons_and_actions):
    for icon_id, icon_cfg in user_icons_and_actions.items():
        icon_class = type(
            "CustomIcon%s" % icon_id.title(),
            (Icon,),
            {
                "_ident": icon_id,
                "_icon_spec": icon_cfg,
                "ident": classmethod(lambda cls: cls._ident),
                "title": classmethod(lambda cls: cls._icon_spec.get("title", cls._ident)),
                "type": classmethod(lambda cls: "custom_icon"),
                "sort_index": lambda self: self._icon_spec.get("sort_index", 15),
                "toplevel": lambda self: self._icon_spec.get("toplevel", False),
                "render": lambda self, *args: (
                    self._icon_spec["icon"],
                    self._icon_spec.get("title"),
                    self._icon_spec.get("url"),
                ),
            },
        )

        icon_and_action_registry.register(icon_class)
