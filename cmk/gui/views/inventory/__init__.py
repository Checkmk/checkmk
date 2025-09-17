#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from cmk.ccc.user import UserId
from cmk.gui import inventory
from cmk.gui.data_source import DataSourceRegistry
from cmk.gui.i18n import _l
from cmk.gui.painter.v0 import Painter, PainterRegistry
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import (
    ColumnSpec,
    FilterName,
    VisualContext,
    VisualLinkSpec,
)
from cmk.gui.views.sorter import Sorter, SorterRegistry
from cmk.gui.views.store import multisite_builtin_views
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.visuals.info import VisualInfo, VisualInfoRegistry

from ._data_sources import ABCDataSourceInventory, RowTableInventory
from ._display_hints import (
    inv_display_hints,
    load_inventory_ui_plugins,
    NodeDisplayHint,
    OrderedColumnDisplayHintsOfView,
    PAINT_FUNCTION_NAME_PREFIX,
    register_display_hints,
    TableWithView,
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
    "InventoryHintSpec",
    "NodeDisplayHint",
    "OrderedColumnDisplayHintsOfView",
    "TableWithView",
    "inv_display_hints",
]


def register_inv_paint_functions(mapping: Mapping[str, object]) -> None:
    for k, v in mapping.items():
        if k.startswith(PAINT_FUNCTION_NAME_PREFIX) and callable(v):
            inv_paint_funtions.register(InvPaintFunction(name=k, func=v))


def _register_painter(
    painter_registry: PainterRegistry,
    from_hint: AttributePainterFromHint | ColumnPainterFromHint | NodePainterFromHint,
) -> None:
    # TODO Clean this up one day
    cls = type(
        "LegacyPainter%s" % from_hint["name"].title(),
        (Painter,),
        {
            "_ident": from_hint["name"],
            "_spec": from_hint,
            "ident": property(lambda s: s._ident),
            "title": lambda s, cell: s._spec["title"],
            "short_title": lambda s, cell: s._spec.get("short", s.title),
            "tooltip_title": lambda s, cell: s._spec.get("tooltip_title", s.title),
            "columns": property(lambda s: s._spec["columns"]),
            "render": lambda self, row, cell, user: from_hint["paint"](row),
            "export_for_python": lambda self, row, cell, user: from_hint["export_for_python"](
                row, cell
            ),
            "export_for_csv": lambda self, row, cell, user: from_hint["export_for_csv"](row, cell),
            "export_for_json": lambda self, row, cell, user: from_hint["export_for_json"](
                row, cell
            ),
            "group_by": lambda self, row, cell: self._spec.get("groupby"),
            "parameters": property(lambda s: s._spec.get("params")),
            "painter_options": property(lambda s: s._spec.get("options", [])),
            "printable": property(lambda s: s._spec.get("printable", True)),
            "sorter": property(lambda s: s._spec.get("sorter", None)),
            "load_inv": property(lambda s: s._spec.get("load_inv", False)),
        },
    )
    painter_registry.register(cls)


def _register_sorter(sorter_registry: SorterRegistry, from_hint: SorterFromHint) -> None:
    sorter_registry.register(
        Sorter(
            ident=from_hint["name"],
            title=from_hint["title"],
            columns=from_hint["columns"],
            sort_function=lambda r1, r2, **_kwargs: from_hint["cmp"](r1, r2),
            load_inv=from_hint.get("load_inv", False),
        )
    )


def _register_views(
    table: TableWithView,
    painters: Sequence[ColumnSpec],
    filters: Iterable[FilterName],
) -> None:
    """Declare two views: one for searching globally. And one for the items of one host"""
    context: VisualContext = {f: {} for f in filters}

    # View for searching for items
    search_view_name = table.name + "_search"
    multisite_builtin_views[search_view_name] = {
        # General options
        "title": _l("Search %s") % table.long_title.lower(),
        "description": (
            _l("A view for searching in the inventory data for %s") % table.long_title.lower()
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
        "datasource": table.name,
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
        "is_show_more": table.is_show_more,
        "owner": UserId.builtin(),
        "add_context_to_title": True,
        "packaged": False,
        "main_menu_search_terms": [],
    }

    # View for the items of one host
    host_view_name = make_table_view_name_of_host(table.name)
    multisite_builtin_views[host_view_name] = {
        # General options
        "title": table.long_title,
        "description": _l("A view for the %s of one host") % table.long_title,
        "hidden": True,
        "hidebutton": False,
        "mustsearch": False,
        "link_from": {
            "single_infos": ["host"],
            "has_inventory_tree": table.path,
        },
        # Columns
        "painters": painters,
        # Filters
        "context": context,
        "icon": table.icon,
        "name": host_view_name,
        "single_infos": ["host"],
        "datasource": table.name,
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
        "is_show_more": table.is_show_more,
        "owner": UserId.builtin(),
        "add_context_to_title": True,
        "packaged": False,
        "main_menu_search_terms": [],
    }


def _register_table_view(
    painter_registry: PainterRegistry,
    sorter_registry: SorterRegistry,
    filter_registry: FilterRegistry,
    visual_info_registry: VisualInfoRegistry,
    data_source_registry: DataSourceRegistry,
    table: TableWithView,
) -> None:
    # Declare the "info" (like a database table)
    visual_info_registry.register(
        type(
            "VisualInfo%s" % table.name.title(),
            (VisualInfo,),
            {
                "_ident": table.name,
                "ident": property(lambda self: self._ident),
                "_title": table.long_title,
                "title": property(lambda self: self._title),
                "_title_plural": table.long_title,
                "title_plural": property(lambda self: self._title_plural),
                "single_spec": property(lambda self: []),
                "single_spec_components": lambda self: [],
            },
        )
    )

    # Create the datasource (like a database view)
    data_source_registry.register(
        type(
            "DataSourceInventory%s" % table.name.title(),
            (ABCDataSourceInventory,),
            {
                "_ident": table.name,
                "_inventory_path": inventory.InventoryPath(
                    path=table.path, source=inventory.TreeSource.table
                ),
                "_title": table.long_inventory_title,
                "_infos": ["host", table.name],
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
    for col_hint in table.columns.values():
        _register_painter(painter_registry, column_painter_from_hint(col_hint))
        _register_sorter(sorter_registry, column_sorter_from_hint(col_hint))
        filter_registry.register(col_hint.filter)

        painters.append(ColumnSpec(col_hint.name))
        filters.append(col_hint.name)

    _register_views(table, painters, filters)


def register_table_views_and_columns(
    painter_registry: PainterRegistry,
    sorter_registry: SorterRegistry,
    filter_registry: FilterRegistry,
    visual_info_registry: VisualInfoRegistry,
    data_source_registry: DataSourceRegistry,
) -> None:
    painter_options = PainterOptions.get_instance()
    register_display_hints(load_inventory_ui_plugins(), inventory_displayhints)
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

        _register_painter(painter_registry, node_painter_from_hint(node_hint, painter_options))

        for key, attr_hint in node_hint.attributes.items():
            _register_painter(
                painter_registry,
                attribute_painter_from_hint(node_hint.path, key, attr_hint),
            )
            _register_sorter(
                sorter_registry,
                attribute_sorter_from_hint(node_hint.path, key, attr_hint),
            )
            filter_registry.register(attr_hint.filter)

        if isinstance(node_hint.table, TableWithView):
            _register_table_view(
                painter_registry,
                sorter_registry,
                filter_registry,
                visual_info_registry,
                data_source_registry,
                node_hint.table,
            )
