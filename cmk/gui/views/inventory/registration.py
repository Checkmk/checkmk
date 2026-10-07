#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.data_source import DataSourceRegistry
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.painter import PainterRegistry
from cmk.gui.painter_options import PainterOptionRegistry
from cmk.gui.type_defs import ViewName, ViewSpec
from cmk.gui.views.row_post_processing import RowPostProcessorRegistry
from cmk.gui.views.sorter import cmp_simple_number, declare_1to1_sorter

from . import _paint_functions, _views
from ._data_sources import DataSourceInventoryHistory
from ._painters import (
    make_inventory_tree_painter,
    make_invhist_changed_painter,
    make_invhist_delta_painter,
    make_invhist_new_painter,
    make_invhist_removed_painter,
    make_invhist_time_painter,
    PainterOptionShowInternalTreePaths,
)
from ._row_post_processor import inventory_row_post_processor
from ._tree_renderer import ajax_inv_render_tree
from .registry import inv_paint_functions


def register(
    page_registry: PageRegistry,
    data_source_registry_: DataSourceRegistry,
    painter_registry_: PainterRegistry,
    painter_option_registry: PainterOptionRegistry,
    multisite_builtin_views: dict[ViewName, ViewSpec],
    row_post_processor_registry: RowPostProcessorRegistry,
) -> None:
    _paint_functions.register(inv_paint_functions)
    page_registry.register(PageEndpoint("ajax_inv_render_tree", ajax_inv_render_tree))
    data_source_registry_.register(DataSourceInventoryHistory)
    painter_registry_.register(make_inventory_tree_painter())
    painter_registry_.register(make_invhist_time_painter())
    painter_registry_.register(make_invhist_delta_painter())
    painter_registry_.register(make_invhist_removed_painter())
    painter_registry_.register(make_invhist_new_painter())
    painter_registry_.register(make_invhist_changed_painter())
    painter_option_registry.register(PainterOptionShowInternalTreePaths())

    declare_1to1_sorter("invhist_time", cmp_simple_number, reverse=True)
    declare_1to1_sorter("invhist_removed", cmp_simple_number)
    declare_1to1_sorter("invhist_new", cmp_simple_number)
    declare_1to1_sorter("invhist_changed", cmp_simple_number)

    _views.register(multisite_builtin_views)
    row_post_processor_registry.register(inventory_row_post_processor)
