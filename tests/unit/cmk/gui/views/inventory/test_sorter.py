#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.structured_data import ImmutableTree, SDKey

from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.painter.v0.helpers import RenderLink
from cmk.gui.painter_options import PainterOptions
from cmk.gui.utils.theme import theme
from cmk.gui.views.inventory import _register_sorter
from cmk.gui.views.inventory._display_hints import (
    _cmp_inv_generic,
    _decorate_sort_function,
    AttributeDisplayHint,
)
from cmk.gui.views.inventory._paint_functions import inv_paint_generic
from cmk.gui.views.inventory._sorter import attribute_sorter_from_hint
from cmk.gui.views.sorter import sorter_registry


def test_registered_sorter_cmp() -> None:
    hint = AttributeDisplayHint(
        title="Product",
        short_title="Product",
        long_title="System ➤ Product",
        paint_function=inv_paint_generic,
        sort_function=_decorate_sort_function(_cmp_inv_generic),
        data_type="str",
        is_show_more=False,
    )
    _register_sorter("inv_key", attribute_sorter_from_hint((), SDKey("key"), hint))
    sorter_cls = sorter_registry.get("inv_key")
    assert sorter_cls is not None
    assert (
        sorter_cls(
            user=user,
            config=active_config,
            request=request,
            painter_options=PainterOptions.get_instance(),
            theme=theme,
            url_renderer=RenderLink(request, response, display_options),
        ).cmp({"host_inventory": ImmutableTree()}, {"host_inventory": ImmutableTree()}, None)
        == 0
    )
