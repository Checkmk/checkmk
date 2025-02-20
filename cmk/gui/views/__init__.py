#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from collections.abc import Mapping
from typing import Any

from cmk.gui import utils, visuals
from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.graphing import PerfometerSpec
from cmk.gui.graphing._translated_metrics import TranslatedMetric
from cmk.gui.i18n import _, _u
from cmk.gui.painter.v0 import register_painter
from cmk.gui.permissions import declare_dynamic_permissions, declare_permission
from cmk.gui.type_defs import Perfdata, VisualLinkSpec
from cmk.gui.view_utils import get_labels, render_labels, render_tag_groups

from . import icon, inventory
from .command import register_legacy_command
from .icon import Icon, icon_and_action_registry
from .inventory import register_table_views_and_columns
from .sorter import register_sorter
from .store import multisite_builtin_views
from .view_choices import format_view_title

# TODO: Kept for compatibility with pre 1.6 plugins. Plugins will not be used anymore, but an error
# will be displayed.
multisite_commands: list[dict[str, Any]] = []
multisite_painters: dict[str, dict[str, Any]] = {}
multisite_sorters: dict[str, Any] = {}
multisite_icons_and_actions: dict[str, dict[str, Any]] = {}


def load_plugins() -> None:
    """Plug-in initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    _register_pre_21_plugin_api()
    utils.load_web_plugins("views", globals())
    inventory.register_inv_paint_functions(globals())

    utils.load_web_plugins("icons", globals())

    register_legacy_icons()

    # TODO: Kept for compatibility with pre 1.6 plugins
    for cmd_spec in multisite_commands:
        register_legacy_command(cmd_spec)

    # Needs to be executed after all plug-ins (built-in and local) are loaded
    register_table_views_and_columns()

    # TODO: Kept for compatibility with pre 1.6 plugins
    for ident, spec in multisite_painters.items():
        register_painter(ident, spec)

    # TODO: Kept for compatibility with pre 1.6 plugins
    for ident, spec in multisite_sorters.items():
        register_sorter(ident, spec)

    visuals.declare_visual_permissions("views", _("views"))

    # Declare permissions for built-in views
    for name, view_spec in multisite_builtin_views.items():
        declare_permission(
            "view.%s" % name,
            format_view_title(name, view_spec),
            "{} - {}".format(name, _u(str(view_spec["description"]))),
            default_authorized_builtin_role_ids,
        )

    # Make sure that custom views also have permissions
    declare_dynamic_permissions(lambda: visuals.declare_custom_permissions("views"))
    declare_dynamic_permissions(lambda: visuals.declare_packaged_visuals_permissions("views"))


def _register_pre_21_plugin_api() -> None:  # pylint: disable=too-many-branches
    """Register pre 2.1 "plug-in API"

    This was never an official API, but the names were used by built-in and also 3rd party plugins.

    Our built-in plug-in have been changed to directly import from the .utils module. We add these old
    names to remain compatible with 3rd party plug-ins for now.

    In the moment we define an official plug-in API, we can drop this and require all plug-ins to
    switch to the new API. Until then let's not bother the users with it.

    CMK-12228
    """
    # Needs to be a local import to not influence the regular plug-in loading order
    import cmk.gui.painter.v0.base as painter_base
    import cmk.gui.painter.v0.helpers as painter_helpers
    import cmk.gui.painter.v0.registry as painter_registry
    import cmk.gui.painter.v1.helpers as painter_v1_helpers
    import cmk.gui.plugins.views as api_module  # pylint: disable=cmk-module-layer-violation
    from cmk.gui import data_source, display_options, exporter, painter_options, visual_link
    from cmk.gui.plugins.views import icons  # pylint: disable=cmk-module-layer-violation

    from . import command, layout, sorter, store

    for name in (
        "ABCDataSource",
        "data_source_registry",
        "row_id",
        "RowTable",
        "DataSourceLivestatus",
        "RowTableLivestatus",
        "query_livestatus",
    ):
        api_module.__dict__[name] = data_source.__dict__[name]

    for name in (
        "Exporter",
        "exporter_registry",
        "output_csv_headers",
    ):
        api_module.__dict__[name] = exporter.__dict__[name]

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
        "declare_1to1_sorter",
        "register_sorter",
        "Sorter",
        "sorter_registry",
        "cmp_custom_variable",
        "cmp_ip_address",
        "cmp_num_split",
        "cmp_simple_number",
        "cmp_simple_string",
        "cmp_string_list",
        "compare_ips",
    ):
        api_module.__dict__[name] = sorter.__dict__[name]

    api_module.__dict__["cmp_service_name_equiv"] = utils.cmp_service_name_equiv

    for name in (
        "get_permitted_views",
        "multisite_builtin_views",
    ):
        api_module.__dict__[name] = store.__dict__[name]

    for name in (
        "inventory_displayhints",
        "InventoryHintSpec",
    ):
        api_module.__dict__[name] = inventory.__dict__[name]

    api_module.__dict__["display_options"] = display_options.display_options
    api_module.__dict__["view_title"] = visuals.view_title

    for name in (
        "Layout",
        "layout_registry",
        "group_value",
    ):
        api_module.__dict__[name] = layout.__dict__[name]

    for name in (
        "Command",
        "command_group_registry",
        "command_registry",
        "CommandActionResult",
        "CommandGroup",
        "CommandSpec",
    ):
        api_module.__dict__[name] = command.__dict__[name]

    for name in (
        "Cell",
        "EmptyCell",
        "CellSpec",
        "Painter",
        "ExportCellContent",
        "join_row",
    ):
        api_module.__dict__[name] = painter_base.__dict__[name]

    for name in (
        "painter_registry",
        "register_painter",
    ):
        api_module.__dict__[name] = painter_registry.__dict__[name]

    for name in (
        "format_plugin_output",
        "get_label_sources",
        "get_tag_groups",
        "paint_host_list",
        "paint_nagiosflag",
        "transform_action_url",
        "render_cache_info",
        "replace_action_url_macros",
    ):
        api_module.__dict__[name] = painter_helpers.__dict__[name]

    for name in (
        "get_perfdata_nth_value",
        "is_stale",
        "paint_stalified",
    ):
        api_module.__dict__[name] = painter_v1_helpers.__dict__[name]

    for name in (
        "render_link_to_view",
        "url_to_visual",
    ):
        api_module.__dict__[name] = visual_link.__dict__[name]

    api_module.__dict__.update(
        {
            "Perfdata": Perfdata,
            "PerfometerSpec": PerfometerSpec,
            "VisualLinkSpec": VisualLinkSpec,
            "TranslatedMetrics": Mapping[str, TranslatedMetric],
            "get_labels": get_labels,
            "render_labels": render_labels,
            "render_tag_groups": render_tag_groups,
        }
    )

    for name in (
        "icon_and_action_registry",
        "Icon",
        "IconRegistry",
    ):
        icons.__dict__[name] = icon.__dict__[name]


# Transform pre 1.6 icon plugins. Deprecate this one day.
def register_legacy_icons() -> None:
    for icon_id, icon_spec in multisite_icons_and_actions.items():
        icon_class = type(
            "LegacyIcon%s" % icon_id.title(),
            (Icon,),
            {
                "_ident": icon_id,
                "_icon_spec": icon_spec,
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
