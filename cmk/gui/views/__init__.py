#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List

import cmk.utils.paths

import cmk.gui.pages
import cmk.gui.utils as utils
import cmk.gui.view_utils
import cmk.gui.views.datasource_selection as _datasource_selection
import cmk.gui.visuals as visuals
from cmk.gui.config import default_authorized_builtin_role_ids, register_post_config_load_hook
from cmk.gui.derived_columns_sorter import DerivedColumnsSorter
from cmk.gui.i18n import _, _u
from cmk.gui.pages import page_registry
from cmk.gui.permissions import (
    declare_dynamic_permissions,
    declare_permission,
    permission_section_registry,
    PermissionSection,
)
from cmk.gui.plugins.views.icons.utils import (
    Icon,
    icon_and_action_registry,
    multisite_icons_and_actions,
)
from cmk.gui.plugins.views.utils import register_legacy_command, register_painter
from cmk.gui.plugins.visuals.utils import visual_type_registry
from cmk.gui.sorter import register_sorter
from cmk.gui.type_defs import Perfdata, PerfometerSpec, TranslatedMetrics
from cmk.gui.view_store import multisite_builtin_views
from cmk.gui.view_utils import get_labels, render_labels, render_tag_groups
from cmk.gui.views.builtin_views import builtin_views
from cmk.gui.views.host_tag_plugins import register_tag_plugins
from cmk.gui.views.inventory import register_table_views_and_columns, update_paint_functions
from cmk.gui.views.page_ajax_filters import AjaxInitialViewFilters
from cmk.gui.views.page_ajax_popup_action_menu import ajax_popup_action_menu
from cmk.gui.views.page_ajax_reschedule import PageRescheduleCheck
from cmk.gui.views.page_create_view import page_create_view
from cmk.gui.views.page_edit_view import (
    format_view_title,
    page_edit_view,
    PageAjaxCascadingRenderPainterParameters,
)
from cmk.gui.views.page_edit_views import page_edit_views
from cmk.gui.views.page_show_view import page_show_view
from cmk.gui.views.visual_type import VisualTypeViews

# TODO: Kept for compatibility with pre 1.6 plugins. Plugins will not be used anymore, but an error
# will be displayed.
multisite_commands: List[Dict[str, Any]] = []
multisite_painters: Dict[str, Dict[str, Any]] = {}
multisite_sorters: Dict[str, Any] = {}


cmk.gui.pages.register("view")(page_show_view)
cmk.gui.pages.register("create_view")(_datasource_selection.page_create_view)
cmk.gui.pages.register("edit_view")(page_edit_view)
cmk.gui.pages.register("edit_views")(page_edit_views)
cmk.gui.pages.register("create_view_infos")(page_create_view)
cmk.gui.pages.register("ajax_popup_action_menu")(ajax_popup_action_menu)
page_registry.register_page("ajax_cascading_render_painer_parameters")(
    PageAjaxCascadingRenderPainterParameters
)
page_registry.register_page("ajax_reschedule")(PageRescheduleCheck)
page_registry.register_page("ajax_initial_view_filters")(AjaxInitialViewFilters)
visual_type_registry.register(VisualTypeViews)
register_post_config_load_hook(register_tag_plugins)


@permission_section_registry.register
class PermissionSectionViews(PermissionSection):
    @property
    def name(self) -> str:
        return "view"

    @property
    def title(self) -> str:
        return _("Views")

    @property
    def do_sort(self):
        return True


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()
    utils.load_web_plugins("views", globals())
    update_paint_functions(globals())

    utils.load_web_plugins("icons", globals())
    utils.load_web_plugins("perfometer", globals())

    transform_old_dict_based_icons()

    # TODO: Kept for compatibility with pre 1.6 plugins
    for cmd_spec in multisite_commands:
        register_legacy_command(cmd_spec)

    multisite_builtin_views.update(builtin_views)

    # Needs to be executed after all plugins (builtin and local) are loaded
    register_table_views_and_columns()

    # TODO: Kept for compatibility with pre 1.6 plugins
    for ident, spec in multisite_painters.items():
        register_painter(ident, spec)

    # TODO: Kept for compatibility with pre 1.6 plugins
    for ident, spec in multisite_sorters.items():
        register_sorter(ident, spec)

    visuals.declare_visual_permissions("views", _("views"))

    # Declare permissions for builtin views
    for name, view_spec in multisite_builtin_views.items():
        declare_permission(
            "view.%s" % name,
            format_view_title(name, view_spec),
            "%s - %s" % (name, _u(str(view_spec["description"]))),
            default_authorized_builtin_role_ids,
        )

    # Make sure that custom views also have permissions
    declare_dynamic_permissions(lambda: visuals.declare_custom_permissions("views"))


def _register_pre_21_plugin_api() -> None:
    """Register pre 2.1 "plugin API"

    This was never an official API, but the names were used by builtin and also 3rd party plugins.

    Our builtin plugin have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plugins for now.

    In the moment we define an official plugin API, we can drop this and require all plugins to
    switch to the new API. Until then let's not bother the users with it.
    """
    # Needs to be a local import to not influence the regular plugin loading order
    import cmk.gui.data_source as data_source
    import cmk.gui.exporter as exporter
    import cmk.gui.livestatus_data_source as livestatus_data_source
    import cmk.gui.painter_options as painter_options
    import cmk.gui.plugins.views as api_module
    import cmk.gui.plugins.views.utils as plugin_utils
    import cmk.gui.sorter as sorter
    import cmk.gui.view_store as view_store
    import cmk.gui.visual_link as visual_link

    for name in (
        "ABCDataSource",
        "data_source_registry",
        "row_id",
        "RowTable",
    ):
        api_module.__dict__[name] = data_source.__dict__[name]

    for name in (
        "Exporter",
        "exporter_registry",
    ):
        api_module.__dict__[name] = exporter.__dict__[name]

    for name in (
        "DataSourceLivestatus",
        "RowTableLivestatus",
        "query_livestatus",
    ):
        api_module.__dict__[name] = livestatus_data_source.__dict__[name]

    for name in (
        "get_graph_timerange_from_painter_options",
        "paint_age",
        "painter_option_registry",
        "PainterOption",
        "PainterOptions",
    ):
        api_module.__dict__[name] = painter_options.__dict__[name]

    for name in (
        "declare_simple_sorter",
        "register_sorter",
        "Sorter",
        "sorter_registry",
    ):
        api_module.__dict__[name] = sorter.__dict__[name]
    api_module.__dict__["DerivedColumnsSorter"] = DerivedColumnsSorter

    for name in (
        "get_permitted_views",
        "multisite_builtin_views",
    ):
        api_module.__dict__[name] = view_store.__dict__[name]

    for name in (
        "Cell",
        "CellSpec",
        "cmp_custom_variable",
        "cmp_ip_address",
        "cmp_num_split",
        "cmp_service_name_equiv",
        "cmp_simple_number",
        "cmp_simple_string",
        "cmp_string_list",
        "Command",
        "command_group_registry",
        "command_registry",
        "CommandActionResult",
        "CommandGroup",
        "CommandSpec",
        "compare_ips",
        "declare_1to1_sorter",
        "display_options",
        "EmptyCell",
        "ExportCellContent",
        "format_plugin_output",
        "get_label_sources",
        "get_perfdata_nth_value",
        "get_tag_groups",
        "group_value",
        "inventory_displayhints",
        "InventoryHintSpec",
        "is_stale",
        "join_row",
        "Layout",
        "layout_registry",
        "output_csv_headers",
        "paint_host_list",
        "paint_nagiosflag",
        "paint_stalified",
        "Painter",
        "painter_registry",
        "register_painter",
        "render_cache_info",
        "replace_action_url_macros",
        "Row",
        "transform_action_url",
        "view_is_enabled",
        "VisualLinkSpec",
    ):
        api_module.__dict__[name] = plugin_utils.__dict__[name]
    api_module.__dict__["view_title"] = visuals.view_title

    for name in (
        "render_link_to_view",
        "url_to_visual",
    ):
        api_module.__dict__[name] = visual_link.__dict__[name]

    api_module.__dict__.update(
        {
            "Perfdata": Perfdata,
            "PerfometerSpec": PerfometerSpec,
            "TranslatedMetrics": TranslatedMetrics,
            "get_labels": get_labels,
            "render_labels": render_labels,
            "render_tag_groups": render_tag_groups,
        }
    )


# Transform pre 1.6 icon plugins. Deprecate this one day.
def transform_old_dict_based_icons():
    for icon_id, icon in multisite_icons_and_actions.items():
        icon_class = type(
            "LegacyIcon%s" % icon_id.title(),
            (Icon,),
            {
                "_ident": icon_id,
                "_icon_spec": icon,
                "ident": classmethod(lambda cls: cls._ident),
                "title": classmethod(lambda cls: cls._title),
                "sort_index": lambda self: self._icon_spec.get("sort_index", 30),
                "toplevel": lambda self: self._icon_spec.get("toplevel", False),
                "render": lambda self, *args: self._icon_spec["paint"](*args),
                "columns": lambda self: self._icon_spec.get("columns", []),
                "host_columns": lambda self: self._icon_spec.get("host_columns", []),
                "service_columns": lambda self: self._icon_spec.get("service_columns", []),
            },
        )

        icon_and_action_registry.register(icon_class)
