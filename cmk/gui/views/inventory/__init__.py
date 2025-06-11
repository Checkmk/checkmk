#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from cmk.ccc.user import UserId

from cmk.utils.structured_data import SDKey, SDPath

from cmk.gui import inventory
from cmk.gui.data_source import data_source_registry
from cmk.gui.i18n import _, _l
from cmk.gui.inventory.filters import FilterInvBool, FilterInvFloat, FilterInvText
from cmk.gui.painter.v0 import Painter, painter_registry
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import (
    ColumnSpec,
    FilterName,
    VisualContext,
    VisualLinkSpec,
)
from cmk.gui.views.sorter import Sorter, sorter_registry
from cmk.gui.views.store import multisite_builtin_views
from cmk.gui.visuals.filter import filter_registry
from cmk.gui.visuals.info import visual_info_registry, VisualInfo

from ._data_sources import ABCDataSourceInventory, RowTableInventory
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
)
from ._sorter import attribute_sorter_from_hint, column_sorter_from_hint, SorterFromHint
from ._tree_renderer import make_table_view_name_of_host
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
            "render": lambda self, row, cell, user: spec["paint"](row),
            "export_for_python": lambda self, row, cell, user: spec["export_for_python"](row, cell),
            "export_for_csv": lambda self, row, cell, user: spec["export_for_csv"](row, cell),
            "export_for_json": lambda self, row, cell, user: spec["export_for_json"](row, cell),
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
    sorter_registry.register(
        Sorter(
            ident=ident,
            title=spec["title"],
            columns=spec["columns"],
            sort_function=lambda r1, r2, **_kwargs: spec["cmp"](r1, r2),
            load_inv=spec.get("load_inv", False),
        )
    )


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
        "main_menu_search_terms": [],
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
        "main_menu_search_terms": [],
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
