#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.inventory as inventory
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import VisualLinkSpec
from cmk.gui.visual_link import url_to_visual

from .base import Icon


class InventoryIcon(Icon):
    @classmethod
    def ident(cls):
        return "inventory"

    @classmethod
    def title(cls) -> str:
        return _("HW/SW inventory")

    def host_columns(self):
        return ["name"]

    def render(  # type: ignore[no-untyped-def]
        self, what, row, tags, custom_vars
    ) -> None | tuple[str, str, str]:
        if (
            what == "host"
            or row.get("service_check_command", "").startswith("check_mk_active-cmk_inv!")
        ) and inventory.has_inventory(row["host_name"]):
            if not user.may("view.inv_host"):
                return None

            v = url_to_visual(row, VisualLinkSpec("views", "inv_host"))
            assert v is not None
            return (
                "inventory",
                _("Show Hardware/Software Inventory of this host"),
                v,
            )
        return None
