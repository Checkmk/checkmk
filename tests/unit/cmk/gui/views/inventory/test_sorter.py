#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.inventory.filters import FilterInvText
from cmk.gui.views.inventory._display_hints import (
    _wrap_paint_function,
    AttributeDisplayHint,
)
from cmk.gui.views.inventory._paint_functions import inv_paint_generic
from cmk.gui.views.inventory._sorter import attribute_sorter_from_hint
from cmk.inventory.raw_paths import InventoryPath, TreeSource
from cmk.inventory.trees import compare_sd_values, ImmutableTree, SDKey, sort_missing_values_first
from cmk.web.utils.request_cache import RequestCache


def test_attribute_sorter_ranks_two_missing_values_equal() -> None:
    name = "inv_key"
    long_title = "System ➤ Product"
    hint = AttributeDisplayHint(
        name=name,
        title="Product",
        short_title="Product",
        long_title=long_title,
        paint_function=_wrap_paint_function(inv_paint_generic),
        sort_function=sort_missing_values_first(compare_sd_values),
        filter=FilterInvText(
            ident=name,
            title=long_title,
            inventory_path=InventoryPath(
                path=(),
                source=TreeSource.attributes,
                key=SDKey("key"),
            ),
            is_show_more=True,
        ),
    )
    assert (
        attribute_sorter_from_hint((), SDKey("key"), hint).cmp(
            {"host_inventory": ImmutableTree()},
            {"host_inventory": ImmutableTree()},
            parameters=None,
            config=active_config,
            request=request,
            request_cache=RequestCache(active_config),
        )
        == 0
    )
