#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable

from cmk.gui.data_source import data_source_registry, register_data_sources
from cmk.gui.pages import PageRegistry
from cmk.gui.painter.v0 import painters
from cmk.gui.painter.v0.base import painter_registry
from cmk.gui.painter_options import painter_option_registry
from cmk.gui.permissions import PermissionSectionRegistry
from cmk.gui.visuals.type import VisualTypeRegistry

from . import icon, inventory, perfometer
from ._permissions import PermissionSectionViews
from .command import (
    command_group_registry,
    command_registry,
    register_command_groups,
    register_commands,
)
from .datasource_selection import page_select_datasource
from .host_tag_plugins import register_tag_plugins
from .icon.page_ajax_popup_action_menu import ajax_popup_action_menu
from .layout import layout_registry, register_layouts
from .page_ajax_filters import AjaxInitialViewFilters
from .page_ajax_reschedule import PageRescheduleCheck
from .page_create_view import page_create_view
from .page_edit_view import page_edit_view, PageAjaxCascadingRenderPainterParameters
from .page_edit_views import page_edit_views
from .page_show_view import page_show_view
from .sorter import register_sorters, sorter_registry
from .visual_type import VisualTypeViews


def register(
    permission_section_registry: PermissionSectionRegistry,
    page_registry: PageRegistry,
    visual_type_registry: VisualTypeRegistry,
    register_post_config_load_hook: Callable[[Callable[[], None]], None],
) -> None:
    register_post_config_load_hook(register_tag_plugins)

    permission_section_registry.register(PermissionSectionViews)

    page_registry.register_page("ajax_cascading_render_painer_parameters")(
        PageAjaxCascadingRenderPainterParameters
    )
    page_registry.register_page("ajax_reschedule")(PageRescheduleCheck)
    page_registry.register_page("ajax_initial_view_filters")(AjaxInitialViewFilters)
    page_registry.register_page_handler("view", page_show_view)
    page_registry.register_page_handler("create_view", page_select_datasource)
    page_registry.register_page_handler("edit_view", page_edit_view)
    page_registry.register_page_handler("edit_views", page_edit_views)
    page_registry.register_page_handler("create_view_infos", page_create_view)
    page_registry.register_page_handler("ajax_popup_action_menu", ajax_popup_action_menu)

    visual_type_registry.register(VisualTypeViews)

    register_layouts(layout_registry)
    painters.register(painter_option_registry, painter_registry)
    register_sorters(sorter_registry)
    register_command_groups(command_group_registry)
    register_commands(command_registry)
    register_data_sources(data_source_registry)
    perfometer.register(sorter_registry, painter_registry)
    icon.register(
        icon.icon_and_action_registry,
        painter_registry,
        permission_section_registry,
        register_post_config_load_hook,
    )
    inventory.register(page_registry)
