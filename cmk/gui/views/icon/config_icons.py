#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.type_defs import BuiltinIconVisibility, IconSpec

from .base import Icon


def update_builtin_icons_from_config(
    icons: dict[str, Icon], builtin_icon_visibility: dict[str, BuiltinIconVisibility]
) -> dict[str, Icon]:
    for icon_id, cfg in builtin_icon_visibility.items():
        icon = icons.get(icon_id)
        if icon is None:
            continue

        if "toplevel" in cfg:
            icon.override_toplevel(cfg["toplevel"])
        if "sort_index" in cfg:
            icon.override_sort_index(cfg["sort_index"])

    return icons


def config_based_icons(user_icons_and_actions: dict[str, IconSpec]) -> dict[str, Icon]:
    return {
        icon_id: type(
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
        )()
        for icon_id, icon_cfg in user_icons_and_actions.items()
    }
