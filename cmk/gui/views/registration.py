#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial

from cmk.gui.data_source import data_source_registry, register_data_sources
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.painter.v0 import painter_registry, painters
from cmk.gui.painter_options import painter_option_registry
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry
from cmk.gui.type_defs import ViewName, ViewSpec
from cmk.gui.visuals.type import VisualTypeRegistry

from . import command, graph, icon, perfometer
from ._join_service_rows import join_service_row_post_processor
from ._permissions import PERMISSION_SECTION_VIEWS
from .builtin_views import builtin_views
from .command import command_group_registry, command_registry
from .datasource_selection import page_select_datasource
from .icon.page_ajax_popup_action_menu import ajax_popup_action_menu
from .inventory import registration as inventory_registration
from .layout import layout_registry, register_layouts
from .page_ajax_filters import AjaxInitialViewFilters
from .page_ajax_reschedule import PageRescheduleCheck
from .page_create_view import page_create_view
from .page_edit_view import page_edit_view, PageAjaxCascadingRenderPainterParameters
from .page_edit_views import page_edit_views
from .page_show_view import page_show_view
from .row_post_processing import RowPostProcessorRegistry
from .sorter import register_sorters, sorter_registry
from .visual_type import VisualTypeViews


def register(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
    page_registry: PageRegistry,
    visual_type_registry: VisualTypeRegistry,
    multisite_builtin_views: dict[ViewName, ViewSpec],
    row_post_processor_registry: RowPostProcessorRegistry,
) -> None:
    multisite_builtin_views.update(builtin_views)

    permission_section_registry.register(PERMISSION_SECTION_VIEWS)

    page_registry.register(
        PageEndpoint(
            "ajax_cascading_render_painer_parameters", PageAjaxCascadingRenderPainterParameters
        )
    )
    page_registry.register(PageEndpoint("ajax_reschedule", PageRescheduleCheck))
    page_registry.register(PageEndpoint("ajax_initial_view_filters", AjaxInitialViewFilters))
    page_registry.register(
        PageEndpoint(
            "view", partial(page_show_view, page_menu_dropdowns_callback=lambda x, y, z: None)
        )
    )
    page_registry.register(PageEndpoint("create_view", page_select_datasource))
    page_registry.register(PageEndpoint("edit_view", page_edit_view))
    page_registry.register(PageEndpoint("edit_views", page_edit_views))
    page_registry.register(PageEndpoint("create_view_infos", page_create_view))
    page_registry.register(PageEndpoint("ajax_popup_action_menu", ajax_popup_action_menu))

    visual_type_registry.register(VisualTypeViews)

    register_layouts(layout_registry)
    painters.register(painter_option_registry, painter_registry)
    register_sorters(sorter_registry)
    command.register(
        command_group_registry, command_registry, permission_section_registry, permission_registry
    )
    register_data_sources(data_source_registry)
    perfometer.register(sorter_registry, painter_registry)
    icon.register(
        icon.icon_and_action_registry,
        painter_registry,
        permission_section_registry,
    )
    inventory_registration.register(
        page_registry,
        data_source_registry,
        painter_registry,
        painter_option_registry,
        multisite_builtin_views,
        row_post_processor_registry,
    )
    graph.register(painter_option_registry, multisite_builtin_views)
    row_post_processor_registry.register(join_service_row_post_processor)
