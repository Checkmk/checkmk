#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import TextInput, ValueSpec


def vs_element_inventory_visible_raw_path() -> tuple[str, ValueSpec]:
    # Via 'Display options::Show internal tree paths' the tree paths are shown as 'path.to.node'.
    # We keep this format in order to easily copy&paste these tree paths to
    # 'Contact groups::Permitted HW/SW Inventory paths'.
    return (
        "visible_raw_path",
        TextInput(
            title=_("Path to categories"),
            size=60,
            allow_empty=False,
        ),
    )


def vs_inventory_path_or_keys_help() -> str:
    return _(
        "Via <tt>Display options > Show internal tree paths</tt>"
        " on the HW/SW Inventory page of a host the internal tree paths leading"
        " to subcategories, the keys of singles values or table column names"
        " become visible. Key columns of tables are marked with '*'. See"
        ' <a href="https://docs.checkmk.com/latest/de/inventory.html">HW/SW Inventory</a>.'
        " for more details about the HW/SW Inventory system."
    )
