#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.inventory._tree import InventoryPath, TreeSource
from cmk.gui.inventory.filters import FilterInvText
from cmk.gui.views.inventory import _register_sorter
from cmk.gui.views.inventory._display_hints import (
    _cmp_inv_generic,
    _decorate_sort_function,
    AttributeDisplayHint,
)
from cmk.gui.views.inventory._paint_functions import inv_paint_generic
from cmk.gui.views.inventory._sorter import attribute_sorter_from_hint
from cmk.gui.views.sorter import sorter_registry
from cmk.utils.structured_data import ImmutableTree, SDKey


def test_registered_sorter_cmp() -> None:
    ident = "inv_key"
    long_title = "System ➤ Product"
    hint = AttributeDisplayHint(
        ident=ident,
        title="Product",
        short_title="Product",
        long_title=long_title,
        paint_function=inv_paint_generic,
        sort_function=_decorate_sort_function(_cmp_inv_generic),
        filter=FilterInvText(
            ident=ident,
            title=long_title,
            inventory_path=InventoryPath(
                path=(),
                source=TreeSource.attributes,
                key=SDKey("key"),
            ),
            is_show_more=True,
        ),
    )
    _register_sorter(ident, attribute_sorter_from_hint((), SDKey("key"), hint))
    sorter = sorter_registry[ident]
    assert (
        sorter.cmp(
            {"host_inventory": ImmutableTree()},
            {"host_inventory": ImmutableTree()},
            parameters=None,
            config=active_config,
            request=request,
        )
        == 0
    )
