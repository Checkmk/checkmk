#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.ccc.hostaddress import HostName

import cmk.utils.paths
from cmk.utils.structured_data import InventoryPaths
from cmk.utils.tags import TagID

from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Row, VisualLinkSpec
from cmk.gui.views.icon import Icon
from cmk.gui.visual_link import url_to_visual


def _has_inventory(host_name: HostName) -> bool:
    return (
        InventoryPaths(cmk.utils.paths.omd_root).inventory_tree(host_name).exists()
        if host_name
        else False
    )


def _render_inventory_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
) -> None | tuple[str, str, str]:
    if (
        what == "host"
        or row.get("service_check_command", "").startswith("check_mk_active-cmk_inv!")
    ) and _has_inventory(row["host_name"]):
        if not user.may("view.inv_host"):
            return None

        v = url_to_visual(row, VisualLinkSpec("views", "inv_host"), request=request)
        assert v is not None
        return (
            "inventory",
            _("Show HW/SW Inventory of this host"),
            v,
        )
    return None


InventoryIcon = Icon(
    ident="inventory",
    title=_l("HW/SW Inventory"),
    host_columns=["name"],
    render=_render_inventory_icon,
)
