#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping, Sequence
from functools import partial
from typing import override

from cmk.ccc.user import UserId
from cmk.gui.data_source import DataSourceRegistry, RowTable
from cmk.gui.i18n import _l
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter import Cell, InternalPainter, PainterContext, PainterRegistry
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import (
    ColumnName,
    ColumnSpec,
    FilterName,
    Row,
    SingleInfos,
    VisualContext,
    VisualLinkSpec,
)
from cmk.gui.valuespec import DictionaryEntry
from cmk.gui.view_utils import CellSpec
from cmk.gui.views.sorter import Sorter, SorterRegistry
from cmk.gui.views.store import multisite_builtin_views
from cmk.gui.visuals.filter import FilterRegistry
from cmk.gui.visuals.filter.components import FilterComponent
from cmk.gui.visuals.info import VisualInfo, VisualInfoRegistry
from cmk.inventory.raw_paths import InventoryPath, TreeSource
from cmk.web.utils.html import HTML
from cmk.web.utils.icons import DynamicIcon, DynamicIconName, StaticIcon

from ._data_sources import ABCDataSourceInventory, RowTableInventory
from ._display_hints import (
    AttributeDisplayHint,
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
    column_painter_from_hint,
    node_painter_from_hint,
    PainterFromHint,
)
from ._sorter import attribute_sorter_from_hint, column_sorter_from_hint, SorterFromHint
from ._tree_renderer import make_table_view_name_of_host
from .registry import (
    inv_paint_functions,
    inventory_displayhints,
    InventoryHintSpec,
    InvPaintFunction,
)

__all__ = [
    "AttributeDisplayHint",
    "InventoryHintSpec",
    "NodeDisplayHint",
    "OrderedColumnDisplayHintsOfView",
    "TableWithView",
    "inv_display_hints",
    "load_inventory_ui_plugins",
]


def register_inv_paint_functions(mapping: Mapping[str, object]) -> None:
    for k, v in mapping.items():
        if k.startswith(PAINT_FUNCTION_NAME_PREFIX) and callable(v):
            inv_paint_functions.register(InvPaintFunction(name=k, func=v))


def _hint_render(
    from_hint: PainterFromHint, row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return from_hint.paint(row)


def _hint_export_for_python(
    from_hint: PainterFromHint, row: Row, cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    return from_hint.export_for_python(row, cell)


def _hint_export_for_csv(
    from_hint: PainterFromHint, row: Row, cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str | HTML:
    return from_hint.export_for_csv(row, cell)


def _hint_export_for_json(
    from_hint: PainterFromHint, row: Row, cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    return from_hint.export_for_json(row, cell)


def _hint_group_by(
    from_hint: PainterFromHint, row: Row, cell: Cell, _context: PainterContext
) -> str | None:
    return from_hint.group_by(row, cell)


def make_inventory_hint_painter(from_hint: PainterFromHint) -> InternalPainter:
    return InternalPainter(
        ident=from_hint.name,
        title=from_hint.title,
        short_title=from_hint.short,
        tooltip_title=from_hint.tooltip_title,
        columns=from_hint.columns,
        sorter=from_hint.sorter,
        printable=from_hint.printable,
        painter_options=from_hint.options,
        load_inv=from_hint.load_inv,
        parameters=from_hint.params,
        group_by=partial(_hint_group_by, from_hint),
        render=partial(_hint_render, from_hint),
        export_for_python=partial(_hint_export_for_python, from_hint),
        export_for_csv=partial(_hint_export_for_csv, from_hint),
        export_for_json=partial(_hint_export_for_json, from_hint),
    )


def _register_painter(painter_registry: PainterRegistry, from_hint: PainterFromHint) -> None:
    painter_registry.register(make_inventory_hint_painter(from_hint))


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
        "title": _l("Search %(title)s") % {"title": table.long_title},
        "description": (
            _l("A view for searching in the inventory data for %(title)s")
            % {"title": table.long_title}
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
    if isinstance(table.icon, StaticIcon):
        main_icon: DynamicIconName = DynamicIconName(table.icon.icon.value)
        if table.icon.emblem is not None:
            icon: DynamicIcon = {"icon": main_icon, "emblem": table.icon.emblem}
        else:
            icon = main_icon
    else:
        icon = table.icon
    multisite_builtin_views[host_view_name] = {
        # General options
        "title": table.long_title,
        "description": _l("A view for the %(title)s of one host") % {"title": table.long_title},
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
        "icon": icon,
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
    class _VisualInfoOfTable(VisualInfo):
        @property
        @override
        def ident(self) -> str:
            return table.name

        @property
        @override
        def title(self) -> str:
            return table.long_title

        @property
        @override
        def title_plural(self) -> str:
            return table.long_title

        @property
        @override
        def single_spec(self) -> list[DictionaryEntry]:
            return []

        @override
        def single_spec_components(self) -> list[FilterComponent]:
            return []

    inventory_path = InventoryPath(path=table.path, source=TreeSource.table)

    class _DataSourceOfTable(ABCDataSourceInventory):
        @property
        @override
        def ident(self) -> str:
            return table.name

        @property
        @override
        def title(self) -> str:
            return table.long_inventory_title

        @property
        @override
        def table(self) -> RowTable:
            return RowTableInventory(table.name, inventory_path)

        @property
        @override
        def infos(self) -> SingleInfos:
            return ["host", table.name]

        @property
        @override
        def keys(self) -> list[ColumnName]:
            return []

        @property
        @override
        def id_keys(self) -> list[ColumnName]:
            return []

        @property
        @override
        def inventory_path(self) -> InventoryPath:
            return inventory_path

        @property
        @override
        def join(self) -> tuple[str, str]:
            return ("services", "host_name")

    visual_info_registry.register(_VisualInfoOfTable)
    data_source_registry.register(_DataSourceOfTable)

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
