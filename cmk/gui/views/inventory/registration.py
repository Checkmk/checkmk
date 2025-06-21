#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.data_source import DataSourceRegistry
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.painter.v0 import PainterRegistry
from cmk.gui.painter_options import PainterOptionRegistry
from cmk.gui.type_defs import ViewName, ViewSpec
from cmk.gui.views.row_post_processing import RowPostProcessorRegistry
from cmk.gui.views.sorter import cmp_simple_number, declare_1to1_sorter

from . import _builtin_display_hints, _paint_functions, _views
from ._data_sources import DataSourceInventoryHistory
from ._painters import (
    PainterInventoryTree,
    PainterInvhistChanged,
    PainterInvhistDelta,
    PainterInvhistNew,
    PainterInvhistRemoved,
    PainterInvhistTime,
    PainterOptionShowInternalTreePaths,
)
from ._row_post_processor import inventory_row_post_processor
from ._tree_renderer import ajax_inv_render_tree
from .registry import inv_paint_funtions, inventory_displayhints


def register(
    page_registry: PageRegistry,
    data_source_registry_: DataSourceRegistry,
    painter_registry_: PainterRegistry,
    painter_option_registry: PainterOptionRegistry,
    multisite_builtin_views: dict[ViewName, ViewSpec],
    row_post_processor_registry: RowPostProcessorRegistry,
) -> None:
    _paint_functions.register(inv_paint_funtions)
    _builtin_display_hints.register(inventory_displayhints)
    page_registry.register(PageEndpoint("ajax_inv_render_tree", ajax_inv_render_tree))
    data_source_registry_.register(DataSourceInventoryHistory)
    painter_registry_.register(PainterInventoryTree)
    painter_registry_.register(PainterInvhistTime)
    painter_registry_.register(PainterInvhistDelta)
    painter_registry_.register(PainterInvhistRemoved)
    painter_registry_.register(PainterInvhistNew)
    painter_registry_.register(PainterInvhistChanged)
    painter_option_registry.register(PainterOptionShowInternalTreePaths())

    declare_1to1_sorter("invhist_time", cmp_simple_number, reverse=True)
    declare_1to1_sorter("invhist_removed", cmp_simple_number)
    declare_1to1_sorter("invhist_new", cmp_simple_number)
    declare_1to1_sorter("invhist_changed", cmp_simple_number)

    _views.register(multisite_builtin_views)
    row_post_processor_registry.register(inventory_row_post_processor)
