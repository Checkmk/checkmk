#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config
from cmk.gui.http import request
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
    hint = AttributeDisplayHint(
        ident="inv_key",
        title="Product",
        short_title="Product",
        long_title="System ➤ Product",
        paint_function=inv_paint_generic,
        sort_function=_decorate_sort_function(_cmp_inv_generic),
        data_type="str",
        is_show_more=False,
    )
    _register_sorter("inv_key", attribute_sorter_from_hint((), SDKey("key"), hint))
    sorter = sorter_registry["inv_key"]
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
