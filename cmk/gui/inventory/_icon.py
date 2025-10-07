#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

import cmk.utils.paths
from cmk.ccc.hostaddress import HostName
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Row, VisualLinkSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.icon import Icon
from cmk.gui.visual_link import url_to_visual
from cmk.inventory.paths import Paths as InventoryPaths
from cmk.utils.tags import TagID


def _has_inventory(host_name: HostName) -> bool:
    tree_path = InventoryPaths(cmk.utils.paths.omd_root).inventory_tree(host_name)
    return (tree_path.path.exists() or tree_path.legacy.exists()) if host_name else False


def _render_inventory_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
    user_permissions: UserPermissions,
) -> None | tuple[str, str, str]:
    if (
        what == "host"
        or row.get("service_check_command", "").startswith("check_mk_active-cmk_inv!")
    ) and _has_inventory(row["host_name"]):
        if not user.may("view.inv_host"):
            return None

        v = url_to_visual(
            row,
            VisualLinkSpec("views", "inv_host"),
            user_permissions,
            request=request,
            force=False,
        )
        assert v is not None
        return (
            "inventory",
            _("Show HW/SW Inventory tree"),
            v,
        )
    return None


InventoryIcon = Icon(
    ident="inventory",
    title=_l("HW/SW Inventory"),
    host_columns=["name"],
    render=_render_inventory_icon,
)


def _has_inventory_history(host_name: HostName) -> bool:
    if not host_name:
        return False
    inv_paths = InventoryPaths(cmk.utils.paths.omd_root)
    for directory in [inv_paths.archive_host(host_name), inv_paths.delta_cache_host(host_name)]:
        try:
            has_history_entries = any(directory.iterdir())
        except FileNotFoundError:
            has_history_entries = False
        if has_history_entries:
            return True
    return False


def _render_inventory_history_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
    user_permissions: UserPermissions,
) -> None | tuple[str, str, str]:
    if (
        what == "host"
        or row.get("service_check_command", "").startswith("check_mk_active-cmk_inv!")
    ) and _has_inventory_history(row["host_name"]):
        if not user.may("view.inv_host"):
            return None

        v = url_to_visual(
            row,
            VisualLinkSpec("views", "inv_host_history"),
            user_permissions,
            request=request,
            force=False,
        )
        assert v is not None
        return (
            "inventory",
            _("Show HW/SW Inventory history"),
            v,
        )
    return None


InventoryHistoryIcon = Icon(
    ident="inventory_history",
    title=_l("HW/SW Inventory history"),
    host_columns=["name"],
    render=_render_inventory_history_icon,
)
