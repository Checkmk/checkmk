#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from cmk.utils.structured_data import SDKey, SDPath
from cmk.utils.user import UserId

import cmk.gui.inventory as inventory
from cmk.gui.data_source import data_source_registry, DataSourceRegistry
from cmk.gui.i18n import _, _l
from cmk.gui.inventory.filters import FilterInvBool, FilterInvFloat, FilterInvText
from cmk.gui.pages import PageRegistry
from cmk.gui.painter.v0.base import Painter, painter_registry, PainterRegistry
from cmk.gui.painter_options import PainterOptionRegistry, PainterOptions
from cmk.gui.type_defs import (
    ColumnSpec,
    FilterName,
    SorterSpec,
    ViewName,
    ViewSpec,
    VisualContext,
    VisualLinkSpec,
)
from cmk.gui.views.sorter import cmp_simple_number, declare_1to1_sorter, Sorter, sorter_registry
from cmk.gui.views.store import multisite_builtin_views
from cmk.gui.visuals.filter import filter_registry
from cmk.gui.visuals.info import visual_info_registry, VisualInfo

from . import _paint_functions, builtin_display_hints
from ._data_sources import ABCDataSourceInventory, DataSourceInventoryHistory, RowTableInventory
from ._display_hints import (
    AttributeDisplayHint,
    inv_display_hints,
    NodeDisplayHint,
    PAINT_FUNCTION_NAME_PREFIX,
    register_display_hints,
)
from ._painters import (
    attribute_painter_from_hint,
    AttributePainterFromHint,
    column_painter_from_hint,
    ColumnPainterFromHint,
    node_painter_from_hint,
    NodePainterFromHint,
    PainterInventoryTree,
    PainterInvhistChanged,
    PainterInvhistDelta,
    PainterInvhistNew,
    PainterInvhistRemoved,
    PainterInvhistTime,
    PainterOptionShowInternalTreePaths,
)
from ._sorter import attribute_sorter_from_hint, column_sorter_from_hint, SorterFromHint
from ._tree_renderer import ajax_inv_render_tree, make_table_view_name_of_host
from .registry import (
    inv_paint_funtions,
    inventory_displayhints,
    InventoryHintSpec,
    InvPaintFunction,
)

__all__ = [
    "inv_display_hints",
    "InventoryHintSpec",
    "NodeDisplayHint",
]


def register_inv_paint_functions(mapping: Mapping[str, object]) -> None:
    for k, v in mapping.items():
        if k.startswith(PAINT_FUNCTION_NAME_PREFIX) and callable(v):
            inv_paint_funtions.register(InvPaintFunction(name=k, func=v))


def register(
    page_registry: PageRegistry,
    data_source_registry_: DataSourceRegistry,
    painter_registry_: PainterRegistry,
    painter_option_registry: PainterOptionRegistry,
    multisite_builtin_views_: dict[ViewName, ViewSpec],
) -> None:
    register_inv_paint_functions(
        # Do no overwrite paint functions from plugins
        {k: v for k, v in vars(_paint_functions).items() if k not in inv_paint_funtions}
    )
    builtin_display_hints.register(inventory_displayhints)
    page_registry.register_page_handler("ajax_inv_render_tree", ajax_inv_render_tree)
    data_source_registry_.register(DataSourceInventoryHistory)
    painter_registry_.register(PainterInventoryTree)
    painter_registry_.register(PainterInvhistTime)
    painter_registry_.register(PainterInvhistDelta)
    painter_registry_.register(PainterInvhistRemoved)
    painter_registry_.register(PainterInvhistNew)
    painter_registry_.register(PainterInvhistChanged)
    painter_option_registry.register(PainterOptionShowInternalTreePaths)

    declare_1to1_sorter("invhist_time", cmp_simple_number, reverse=True)
    declare_1to1_sorter("invhist_removed", cmp_simple_number)
    declare_1to1_sorter("invhist_new", cmp_simple_number)
    declare_1to1_sorter("invhist_changed", cmp_simple_number)

    multisite_builtin_views_.update(
        {
            "inv_host": _INV_VIEW_HOST,
            "inv_hosts_cpu": _INV_VIEW_HOST_CPU,
            "inv_hosts_ports": _INV_VIEW_HOST_PORTS,
            "inv_host_history": _INV_VIEW_HOST_HISTORY,
        }
    )


def _register_painter(
    ident: str, spec: AttributePainterFromHint | ColumnPainterFromHint | NodePainterFromHint
) -> None:
    # TODO Clean this up one day
    cls = type(
        "LegacyPainter%s" % ident.title(),
        (Painter,),
        {
            "_ident": ident,
            "_spec": spec,
            "ident": property(lambda s: s._ident),
            "title": lambda s, cell: s._spec["title"],
            "short_title": lambda s, cell: s._spec.get("short", s.title),
            "tooltip_title": lambda s, cell: s._spec.get("tooltip_title", s.title),
            "columns": property(lambda s: s._spec["columns"]),
            "render": lambda self, row, cell: spec["paint"](row),
            "export_for_python": lambda self, row, cell: spec["export_for_python"](row, cell),
            "export_for_csv": lambda self, row, cell: spec["export_for_csv"](row, cell),
            "export_for_json": lambda self, row, cell: spec["export_for_json"](row, cell),
            "group_by": lambda self, row, cell: self._spec.get("groupby"),
            "parameters": property(lambda s: s._spec.get("params")),
            "painter_options": property(lambda s: s._spec.get("options", [])),
            "printable": property(lambda s: s._spec.get("printable", True)),
            "sorter": property(lambda s: s._spec.get("sorter", None)),
            "load_inv": property(lambda s: s._spec.get("load_inv", False)),
        },
    )
    painter_registry.register(cls)


def _register_sorter(ident: str, spec: SorterFromHint) -> None:
    # TODO Clean this up one day
    cls = type(
        "LegacySorter%s" % str(ident).title(),
        (Sorter,),
        {
            "_ident": ident,
            "_spec": spec,
            "ident": property(lambda s: s._ident),
            "title": property(lambda s: s._spec["title"]),
            "columns": property(lambda s: s._spec["columns"]),
            "load_inv": property(lambda s: s._spec.get("load_inv", False)),
            "cmp": lambda self, r1, r2, p: spec["cmp"](r1, r2),
        },
    )
    sorter_registry.register(cls)


def _make_attribute_filter(
    ident: str, path: SDPath, key: SDKey, hint: AttributeDisplayHint
) -> FilterInvText | FilterInvBool | FilterInvFloat:
    inventory_path = inventory.InventoryPath(
        path=path,
        source=inventory.TreeSource.attributes,
        key=key,
    )
    match hint.data_type:
        case "str":
            return FilterInvText(
                ident=ident,
                title=hint.long_title,
                inventory_path=inventory_path,
                is_show_more=hint.is_show_more,
            )
        case "bool":
            return FilterInvBool(
                ident=ident,
                title=hint.long_title,
                inventory_path=inventory_path,
                is_show_more=hint.is_show_more,
            )
        case "bytes" | "bytes_rounded":
            unit = _("MB")
            scale = 1024 * 1024
        case "hz":
            unit = _("MHz")
            scale = 1000000
        case "volt":
            unit = _("Volt")
            scale = 1
        case "timestamp":
            unit = _("secs")
            scale = 1
        case _:
            unit = ""
            scale = 1

    return FilterInvFloat(
        ident=ident,
        title=hint.long_title,
        inventory_path=inventory_path,
        unit=unit,
        scale=scale,
        is_show_more=hint.is_show_more,
    )


def _register_views(
    hint: NodeDisplayHint,
    painters: Sequence[ColumnSpec],
    filters: Iterable[FilterName],
) -> None:
    """Declare two views: one for searching globally. And one for the items of one host"""
    context: VisualContext = {f: {} for f in filters}

    # View for searching for items
    search_view_name = hint.table_view_name + "_search"
    multisite_builtin_views[search_view_name] = {
        # General options
        "title": _l("Search %s") % hint.title.lower(),
        "description": (
            _l("A view for searching in the inventory data for %s") % hint.title.lower()
        ),
        "hidden": False,
        "hidebutton": False,
        "mustsearch": True,
        # Columns
        "painters": [
            ColumnSpec(
                name="host",
                link_spec=VisualLinkSpec(type_name="views", name="inv_host"),
            ),
            *painters,
        ],
        # Filters
        "context": {
            **{
                f: {}
                for f in [
                    "siteopt",
                    "hostregex",
                    "hostgroups",
                    "opthostgroup",
                    "opthost_contactgroup",
                    "host_address",
                    "host_tags",
                    "hostalias",
                    "host_favorites",
                ]
            },
            **context,
        },
        "name": search_view_name,
        "link_from": {},
        "icon": None,
        "single_infos": [],
        "datasource": hint.table_view_name,
        "topic": "inventory",
        "sort_index": 30,
        "public": True,
        "layout": "table",
        "num_columns": 1,
        "browser_reload": 0,
        "column_headers": "pergroup",
        "user_sortable": True,
        "play_sounds": False,
        "force_checkboxes": False,
        "mobile": False,
        "group_painters": [],
        "sorters": [],
        "is_show_more": hint.table_is_show_more,
        "owner": UserId.builtin(),
        "add_context_to_title": True,
        "packaged": False,
        "megamenu_search_terms": [],
    }

    # View for the items of one host
    host_view_name = make_table_view_name_of_host(hint.table_view_name)
    multisite_builtin_views[host_view_name] = {
        # General options
        "title": hint.title,
        "description": _l("A view for the %s of one host") % hint.title,
        "hidden": True,
        "hidebutton": False,
        "mustsearch": False,
        "link_from": {
            "single_infos": ["host"],
            "has_inventory_tree": hint.path,
        },
        # Columns
        "painters": painters,
        # Filters
        "context": context,
        "icon": hint.icon,
        "name": host_view_name,
        "single_infos": ["host"],
        "datasource": hint.table_view_name,
        "topic": "inventory",
        "sort_index": 30,
        "public": True,
        "layout": "table",
        "num_columns": 1,
        "browser_reload": 0,
        "column_headers": "pergroup",
        "user_sortable": True,
        "play_sounds": False,
        "force_checkboxes": False,
        "mobile": False,
        "group_painters": [],
        "sorters": [],
        "is_show_more": hint.table_is_show_more,
        "owner": UserId.builtin(),
        "add_context_to_title": True,
        "packaged": False,
        "megamenu_search_terms": [],
    }


def _register_table_view(node_hint: NodeDisplayHint) -> None:
    if not node_hint.table_view_name:
        return

    # Declare the "info" (like a database table)
    visual_info_registry.register(
        type(
            "VisualInfo%s" % node_hint.table_view_name.title(),
            (VisualInfo,),
            {
                "_ident": node_hint.table_view_name,
                "ident": property(lambda self: self._ident),
                "_title": node_hint.title,
                "title": property(lambda self: self._title),
                "_title_plural": node_hint.title,
                "title_plural": property(lambda self: self._title_plural),
                "single_spec": property(lambda self: []),
            },
        )
    )

    # Create the datasource (like a database view)
    data_source_registry.register(
        type(
            "DataSourceInventory%s" % node_hint.table_view_name.title(),
            (ABCDataSourceInventory,),
            {
                "_ident": node_hint.table_view_name,
                "_inventory_path": inventory.InventoryPath(
                    path=node_hint.path, source=inventory.TreeSource.table
                ),
                "_title": node_hint.long_inventory_table_title,
                "_infos": ["host", node_hint.table_view_name],
                "ident": property(lambda s: s._ident),
                "title": property(lambda s: s._title),
                "table": property(lambda s: RowTableInventory(s._ident, s._inventory_path)),
                "infos": property(lambda s: s._infos),
                "keys": property(lambda s: []),
                "id_keys": property(lambda s: []),
                "inventory_path": property(lambda s: s._inventory_path),
                "join": ("services", "host_name"),
            },
        )
    )

    painters: list[ColumnSpec] = []
    filters = []
    for key, col_hint in node_hint.columns.items():
        col_hint_ident = node_hint.column_ident(key)
        _register_painter(col_hint_ident, column_painter_from_hint(col_hint_ident, col_hint))
        _register_sorter(col_hint_ident, column_sorter_from_hint(col_hint_ident, col_hint))
        filter_registry.register(
            col_hint.filter_class(
                inv_info=node_hint.table_view_name,
                ident=col_hint_ident,
                title=col_hint.long_title,
            )
        )

        painters.append(ColumnSpec(col_hint_ident))
        filters.append(col_hint_ident)

    _register_views(node_hint, painters, filters)


def register_table_views_and_columns() -> None:
    register_display_hints(inventory_displayhints)
    painter_options = PainterOptions.get_instance()
    for node_hint in inv_display_hints:
        if "*" in node_hint.path:
            # FIXME DYNAMIC-PATHS
            # For now we have to exclude these kind of paths due to the following reason:
            # During registration of table views only these 'abc' paths are available which are
            # used to create view names, eg: 'invfoo*bar'.
            # But in tree views of a host we have concrete paths and therefore view names like
            #   'invfooNAME1bar', 'invfooNAME2bar', ...
            # Moreover we would use the 'abc' path in order to find the node/table with these views.
            # Have a look at the related data sources, eg.
            #   'DataSourceInventory' uses 'RowTableInventory'
            continue

        _register_painter(node_hint.ident, node_painter_from_hint(node_hint, painter_options))

        for key, attr_hint in node_hint.attributes.items():
            attr_ident = node_hint.attribute_ident(key)
            _register_painter(
                attr_ident, attribute_painter_from_hint(node_hint.path, key, attr_ident, attr_hint)
            )
            _register_sorter(attr_ident, attribute_sorter_from_hint(node_hint.path, key, attr_hint))
            filter_registry.register(
                _make_attribute_filter(attr_ident, node_hint.path, key, attr_hint)
            )

        _register_table_view(node_hint)


#   .--views---------------------------------------------------------------.
#   |                            _                                         |
#   |                     __   _(_) _____      _____                       |
#   |                     \ \ / / |/ _ \ \ /\ / / __|                      |
#   |                      \ V /| |  __/\ V  V /\__ \                      |
#   |                       \_/ |_|\___| \_/\_/ |___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# View for Inventory tree of one host
_INV_VIEW_HOST = ViewSpec(
    {
        # General options
        "datasource": "hosts",
        "topic": "inventory",
        "title": _("Inventory of host"),
        "description": _("The complete hardware- and software inventory of a host"),
        "icon": "inventory",
        "hidebutton": False,
        "public": True,
        "hidden": True,
        "link_from": {
            "single_infos": ["host"],
            # Check root of inventory tree
            "has_inventory_tree": tuple(),
        },
        # Layout options
        "layout": "dataset",
        "num_columns": 1,
        "browser_reload": 0,
        "column_headers": "pergroup",
        "user_sortable": False,
        "play_sounds": False,
        "force_checkboxes": False,
        "mustsearch": False,
        "mobile": False,
        # Columns
        "group_painters": [],
        "painters": [
            ColumnSpec(
                name="host",
                link_spec=VisualLinkSpec(type_name="views", name="host"),
            ),
            ColumnSpec(name="inventory_tree"),
        ],
        "sorters": [],
        "owner": UserId.builtin(),
        "name": "inv_host",
        "single_infos": ["host"],
        "context": {},
        "add_context_to_title": True,
        "sort_index": 99,
        "is_show_more": False,
        "packaged": False,
        "megamenu_search_terms": [],
    }
)

# View with table of all hosts, with some basic information
_INV_VIEW_HOST_CPU = ViewSpec(
    {
        # General options
        "datasource": "hosts",
        "topic": "inventory",
        "sort_index": 10,
        "title": _("CPU inventory of all hosts"),
        "description": _("A list of all hosts with some CPU related inventory data"),
        "public": True,
        "hidden": False,
        "hidebutton": False,
        "is_show_more": True,
        # Layout options
        "layout": "table",
        "num_columns": 1,
        "browser_reload": 0,
        "column_headers": "pergroup",
        "user_sortable": True,
        "play_sounds": False,
        "force_checkboxes": False,
        "mustsearch": False,
        "mobile": False,
        # Columns
        "group_painters": [],
        "painters": [
            ColumnSpec(
                name="host",
                link_spec=VisualLinkSpec(type_name="views", name="inv_host"),
            ),
            ColumnSpec(name="inv_software_os_name"),
            ColumnSpec(name="inv_hardware_cpu_cpus"),
            ColumnSpec(name="inv_hardware_cpu_cores"),
            ColumnSpec(name="inv_hardware_cpu_max_speed"),
            ColumnSpec(
                name="perfometer",
                join_value="CPU load",
            ),
            ColumnSpec(
                name="perfometer",
                join_value="CPU utilization",
            ),
        ],
        "sorters": [],
        "owner": UserId.builtin(),
        "name": "inv_hosts_cpu",
        "single_infos": [],
        "context": {
            "has_inv": {"is_has_inv": "1"},
            "inv_hardware_cpu_cpus": {},
            "inv_hardware_cpu_cores": {},
            "inv_hardware_cpu_max_speed": {},
        },
        "link_from": {},
        "icon": None,
        "add_context_to_title": True,
        "packaged": False,
        "megamenu_search_terms": [],
    }
)

# View with available and used ethernet ports
_INV_VIEW_HOST_PORTS = ViewSpec(
    {
        # General options
        "datasource": "hosts",
        "topic": "inventory",
        "sort_index": 20,
        "title": _("Switch port statistics"),
        "description": _(
            "A list of all hosts with statistics about total, used and free networking interfaces"
        ),
        "public": True,
        "hidden": False,
        "hidebutton": False,
        "is_show_more": False,
        # Layout options
        "layout": "table",
        "num_columns": 1,
        "browser_reload": 0,
        "column_headers": "pergroup",
        "user_sortable": True,
        "play_sounds": False,
        "force_checkboxes": False,
        "mustsearch": False,
        "mobile": False,
        # Columns
        "group_painters": [],
        "painters": [
            ColumnSpec(
                name="host",
                link_spec=VisualLinkSpec(
                    type_name="views",
                    name=make_table_view_name_of_host("invinterface"),
                ),
            ),
            ColumnSpec(name="inv_hardware_system_product"),
            ColumnSpec(name="inv_networking_total_interfaces"),
            ColumnSpec(name="inv_networking_total_ethernet_ports"),
            ColumnSpec(name="inv_networking_available_ethernet_ports"),
        ],
        "sorters": [SorterSpec(sorter="inv_networking_available_ethernet_ports", negate=True)],
        "owner": UserId.builtin(),
        "name": "inv_hosts_ports",
        "single_infos": [],
        "context": {
            "has_inv": {"is_has_inv": "1"},
            "siteopt": {},
            "hostregex": {},
        },
        "link_from": {},
        "icon": None,
        "add_context_to_title": True,
        "packaged": False,
        "megamenu_search_terms": [],
    }
)

_INV_VIEW_HOST_HISTORY = ViewSpec(
    {
        # General options
        "datasource": "invhist",
        "topic": "inventory",
        "title": _("Inventory history of host"),
        "description": _("The history for changes in hardware- and software inventory of a host"),
        "icon": {
            "icon": "inventory",
            "emblem": "time",
        },
        "hidebutton": False,
        "public": True,
        "hidden": True,
        "is_show_more": True,
        "link_from": {
            "single_infos": ["host"],
            "has_inventory_tree_history": tuple(),
        },
        # Layout options
        "layout": "table",
        "num_columns": 1,
        "browser_reload": 0,
        "column_headers": "pergroup",
        "user_sortable": True,
        "play_sounds": False,
        "force_checkboxes": False,
        "mustsearch": False,
        "mobile": False,
        # Columns
        "group_painters": [],
        "painters": [
            ColumnSpec(name="invhist_time"),
            ColumnSpec(name="invhist_removed"),
            ColumnSpec(name="invhist_new"),
            ColumnSpec(name="invhist_changed"),
            ColumnSpec(name="invhist_delta"),
        ],
        "sorters": [SorterSpec(sorter="invhist_time", negate=False)],
        "owner": UserId.builtin(),
        "name": "inv_host_history",
        "single_infos": ["host"],
        "context": {},
        "add_context_to_title": True,
        "sort_index": 99,
        "packaged": False,
        "megamenu_search_terms": [],
    }
)
