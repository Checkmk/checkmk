#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

import cmk.utils.paths
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Row, VisualLinkSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.icon import Icon, IconConfig
from cmk.gui.visual_link import url_to_visual
from cmk.inventory.paths import has_history, has_inventory_tree, InventoryPaths
from cmk.ruleset_matcher.tags import TagID
from cmk.web.utils.icons import DynamicIcon, IconNames, StaticIcon


def _is_inventory_row_of_a_host(what: Literal["host", "service"], row: Row) -> bool:
    return bool(row["host_name"]) and (
        what == "host"
        or row.get("service_check_command", "").startswith("check_mk_active-cmk_inv!")
    )


def _link_to_view(
    row: Row, user_permissions: UserPermissions, view_name: str, title: str
) -> tuple[StaticIcon, str, str] | None:
    if not user.may("view.inv_host"):
        return None
    url = url_to_visual(
        row,
        VisualLinkSpec("views", view_name),
        user_permissions,
        request=request,
        force=False,
    )
    assert url is not None
    return StaticIcon(IconNames.inventory), title, url


def _render_inventory_icon(
    what: Literal["host", "service"],
    row: Row,
    _tags: Sequence[TagID],
    _custom_vars: Mapping[str, str],
    user_permissions: UserPermissions,
    _icon_config: IconConfig,
) -> None | tuple[StaticIcon | DynamicIcon, str, str]:
    if _is_inventory_row_of_a_host(what, row) and has_inventory_tree(
        InventoryPaths(cmk.utils.paths.omd_root), row["host_name"]
    ):
        return _link_to_view(row, user_permissions, "inv_host", _("Show HW/SW inventory tree"))
    return None


InventoryIcon = Icon(
    ident="inventory",
    title=_l("HW/SW inventory"),
    host_columns=["name"],
    render=_render_inventory_icon,
)


def _render_inventory_history_icon(
    what: Literal["host", "service"],
    row: Row,
    _tags: Sequence[TagID],
    _custom_vars: Mapping[str, str],
    user_permissions: UserPermissions,
    _icon_config: IconConfig,
) -> None | tuple[StaticIcon | DynamicIcon, str, str]:
    if _is_inventory_row_of_a_host(what, row) and has_history(
        InventoryPaths(cmk.utils.paths.omd_root), row["host_name"]
    ):
        return _link_to_view(
            row, user_permissions, "inv_host_history", _("Show HW/SW inventory history")
        )
    return None


InventoryHistoryIcon = Icon(
    ident="inventory_history",
    title=_l("HW/SW inventory history"),
    host_columns=["name"],
    render=_render_inventory_history_icon,
)
