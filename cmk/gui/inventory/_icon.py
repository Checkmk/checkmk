#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.utils.tags import TagID

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Row, VisualLinkSpec
from cmk.gui.views.icon import Icon
from cmk.gui.visual_link import url_to_visual

from ._store import has_inventory


class InventoryIcon(Icon):
    @classmethod
    def ident(cls) -> str:
        return "inventory"

    @classmethod
    def title(cls) -> str:
        return _("HW/SW Inventory")

    def host_columns(self) -> list[str]:
        return ["name"]

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> None | tuple[str, str, str]:
        if (
            what == "host"
            or row.get("service_check_command", "").startswith("check_mk_active-cmk_inv!")
        ) and has_inventory(row["host_name"]):
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
