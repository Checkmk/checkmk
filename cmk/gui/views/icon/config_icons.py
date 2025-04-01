#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.i18n import _
from cmk.gui.permissions import declare_permission, permission_registry
from cmk.gui.type_defs import BuiltinIconVisibility, IconSpec

from .base import Icon


def update_builtin_icons_from_config(
    icons: dict[str, Icon], builtin_icon_visibility: dict[str, BuiltinIconVisibility]
) -> dict[str, Icon]:
    for icon_id, cfg in builtin_icon_visibility.items():
        icon = icons.get(icon_id)
        if icon is None:
            continue

        icon.override_toplevel(cfg.get("toplevel"))
        icon.override_sort_index(cfg.get("sort_index"))

    return icons


def config_based_icons(user_icons_and_actions: dict[str, IconSpec]) -> dict[str, Icon]:
    declare_icons_and_actions_perm(user_icons_and_actions)

    return {
        icon_id: Icon(
            ident=icon_id,
            title=icon_cfg.get("title", icon_id),
            columns=[],
            host_columns=[],
            service_columns=[],
            render=lambda *args: (  # type: ignore[arg-type]
                icon_cfg["icon"],
                icon_cfg.get("title"),
                icon_cfg.get("url"),
            ),
            type_="custom_icon",
            sort_index=icon_cfg.get("sort_index", 15),
            toplevel=icon_cfg.get("toplevel", False),
        )
        for icon_id, icon_cfg in user_icons_and_actions.items()
    }


def declare_icons_and_actions_perm(icons: dict[str, IconSpec]) -> None:
    for ident, _icon in icons.items():
        if (permname := f"icons_and_actions.{ident}") in permission_registry:
            continue

        declare_permission(
            permname,
            ident,
            _("Allow to see the icon %s in the host and service views") % ident,
            default_authorized_builtin_role_ids,
        )
