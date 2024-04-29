#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import (
    ImmutableAttributes,
    ImmutableDeltaTree,
    ImmutableTree,
    SDKey,
    SDPath,
    SDRawDeltaTree,
    SDRawTree,
    SDValue,
)
from cmk.utils.user import UserId

import cmk.gui.inventory as inventory
import cmk.gui.sites as sites
from cmk.gui.data_source import data_source_registry, DataSourceRegistry
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.pages import PageRegistry
from cmk.gui.painter.v0.base import Cell, Painter, PainterRegistry, register_painter
from cmk.gui.painter_options import paint_age, PainterOption, PainterOptionRegistry, PainterOptions
from cmk.gui.type_defs import (
    ColumnName,
    ColumnSpec,
    FilterName,
    Icon,
    PainterParameters,
    Row,
    SorterSpec,
    ViewName,
    ViewSpec,
    VisualContext,
    VisualLinkSpec,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.valuespec import Checkbox, Dictionary, FixedValue, ValueSpec
from cmk.gui.view_utils import CellSpec, CSVExportError
from cmk.gui.views.sorter import cmp_simple_number, declare_1to1_sorter, register_sorter
from cmk.gui.views.store import multisite_builtin_views
from cmk.gui.visuals.filter import filter_registry
from cmk.gui.visuals.info import visual_info_registry, VisualInfo

from . import _paint_functions, builtin_display_hints
from ._data_sources import ABCDataSourceInventory, DataSourceInventoryHistory, RowTableInventory
from ._display_hints import (
    AttributeDisplayHint,
    ColumnDisplayHint,
    DISPLAY_HINTS,
    NodeDisplayHint,
    PAINT_FUNCTION_NAME_PREFIX,
)
from ._tree_renderer import (
    ajax_inv_render_tree,
    compute_cell_spec,
    make_table_view_name_of_host,
    SDItem,
    TreeRenderer,
)
from .registry import (
    inv_paint_funtions,
    inventory_displayhints,
    InventoryHintSpec,
    InvPaintFunction,
)

__all__ = [
    "DISPLAY_HINTS",
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
    painter_registry: PainterRegistry,
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
    painter_registry.register(PainterInventoryTree)
    painter_registry.register(PainterInvhistTime)
    painter_registry.register(PainterInvhistDelta)
    painter_registry.register(PainterInvhistRemoved)
    painter_registry.register(PainterInvhistNew)
    painter_registry.register(PainterInvhistChanged)
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
        }
    )


class MultipleInventoryTreesError(Exception):
    pass


def _validate_inventory_tree_uniqueness(row: Row) -> None:
    raw_hostname = row.get("host_name")
    assert isinstance(raw_hostname, str)

    if (
        len(
            sites_with_same_named_hosts := _get_sites_with_same_named_hosts_cache().get(
                HostName(raw_hostname), []
            )
        )
        > 1
    ):
        html.show_error(
            _("Cannot display inventory tree of host '%s': Found this host on multiple sites: %s")
            % (raw_hostname, ", ".join(sites_with_same_named_hosts))
        )
        raise MultipleInventoryTreesError()


@request_memoize()
def _get_sites_with_same_named_hosts_cache() -> Mapping[HostName, Sequence[SiteId]]:
    cache: dict[HostName, list[SiteId]] = {}
    query_str = "GET hosts\nColumns: host_name\n"
    with sites.prepend_site():
        for row in sites.live().query(query_str):
            cache.setdefault(HostName(row[1]), []).append(SiteId(row[0]))
    return cache


class PainterOptionShowInternalTreePaths(PainterOption):
    @property
    def ident(self) -> str:
        return "show_internal_tree_paths"

    @property
    def valuespec(self) -> ValueSpec:
        return Checkbox(
            title=_("Show internal tree paths"),
            default_value=False,
        )


class PainterInventoryTree(Painter):
    @property
    def ident(self) -> str:
        return "inventory_tree"

    def title(self, cell):
        return _("Inventory Tree")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_inventory", "host_structured_status"]

    @property
    def painter_options(self):
        return ["show_internal_tree_paths"]

    @property
    def load_inv(self):
        return True

    def _compute_data(self, row: Row, cell: Cell) -> ImmutableTree:
        try:
            _validate_inventory_tree_uniqueness(row)
        except MultipleInventoryTreesError:
            return ImmutableTree()

        return row.get("host_inventory", ImmutableTree())

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if not (tree := self._compute_data(row, cell)):
            return "", ""

        tree_renderer = TreeRenderer(
            row["site"],
            row["host_name"],
            show_internal_tree_paths=self._painter_options.get("show_internal_tree_paths"),
        )

        with output_funnel.plugged():
            tree_renderer.show(tree, self.request)
            code = HTML(output_funnel.drain())

        return "invtree", code

    def export_for_python(self, row: Row, cell: Cell) -> SDRawTree:
        return self._compute_data(row, cell).serialize()

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> SDRawTree:
        return self._compute_data(row, cell).serialize()


# .
#   .--columns-------------------------------------------------------------.
#   |                          _                                           |
#   |                 ___ ___ | |_   _ _ __ ___  _ __  ___                 |
#   |                / __/ _ \| | | | | '_ ` _ \| '_ \/ __|                |
#   |               | (_| (_) | | |_| | | | | | | | | \__ \                |
#   |                \___\___/|_|\__,_|_| |_| |_|_| |_|___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def register_table_views_and_columns() -> None:
    # Parse legacy display hints
    DISPLAY_HINTS.parse(inventory_displayhints)

    # Now register table views or columns (which need new display hints)
    _register_table_views_and_columns()


def _register_table_views_and_columns() -> None:
    # create painters for node with a display hint
    painter_options = PainterOptions.get_instance()
    for node_hint in DISPLAY_HINTS:
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

        _register_node_painter(node_hint, painter_options=painter_options)

        for attr_hint in node_hint.attributes.values():
            _register_attribute_column(attr_hint)

        _register_table_view(node_hint)


def _register_node_painter(node_hint: NodeDisplayHint, *, painter_options: PainterOptions) -> None:
    """Declares painters for (sub) trees on all host related datasources."""
    register_painter(
        node_hint.ident,
        {
            "title": node_hint.long_inventory_title,
            "short": node_hint.short_title,
            "columns": ["host_inventory", "host_structured_status"],
            "options": ["show_internal_tree_paths"],
            "params": Dictionary(
                title=_("Report options"),
                elements=[
                    (
                        "use_short",
                        Checkbox(
                            title=_("Use short title in reports header"),
                            default_value=False,
                        ),
                    ),
                ],
                required_keys=["use_short"],
            ),
            # Only attributes can be shown in reports. There is currently no way to render trees.
            # The HTML code would simply be stripped by the default rendering mechanism which does
            # not look good for the HW/SW inventory tree
            "printable": False,
            "load_inv": True,
            "sorter": node_hint.ident,
            "paint": lambda row: _paint_host_inventory_tree(
                row, node_hint.path, painter_options=painter_options
            ),
            "export_for_python": lambda row, cell: (
                _compute_node_painter_data(row, node_hint.path).serialize()
            ),
            "export_for_csv": lambda row, cell: _export_node_for_csv(),
            "export_for_json": lambda row, cell: (
                _compute_node_painter_data(row, node_hint.path).serialize()
            ),
        },
    )


def _compute_node_painter_data(row: Row, path: SDPath) -> ImmutableTree:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return ImmutableTree()

    return row.get("host_inventory", ImmutableTree()).get_tree(path)


def _paint_host_inventory_tree(
    row: Row, path: SDPath, *, painter_options: PainterOptions
) -> CellSpec:
    if not (tree := _compute_node_painter_data(row, path)):
        return "", ""

    tree_renderer = TreeRenderer(
        row["site"],
        row["host_name"],
        show_internal_tree_paths=painter_options.get("show_internal_tree_paths"),
    )

    with output_funnel.plugged():
        tree_renderer.show(tree, request)
        code = HTML(output_funnel.drain())

    return "invtree", code


def _export_node_for_csv() -> str | HTML:
    raise CSVExportError()


def _register_attribute_column(hint: AttributeDisplayHint) -> None:
    """Declares painters, sorters and filters to be used in views based on all host related
    datasources."""
    long_inventory_title = hint.long_inventory_title

    # Declare column painter
    register_painter(
        hint.ident,
        {
            "title": long_inventory_title,
            # The short titles (used in column headers) may overlap for different painters, e.g.:
            # - BIOS > Version
            # - Firmware > Version
            # We want to keep column titles short, yet, to make up for overlapping we show the
            # long_title in the column title tooltips
            "short": hint.short_title,
            "tooltip_title": hint.long_title,
            "columns": ["host_inventory", "host_structured_status"],
            "options": ["show_internal_tree_paths"],
            "params": Dictionary(
                title=_("Report options"),
                elements=[
                    (
                        "use_short",
                        Checkbox(
                            title=_("Use short title in reports header"),
                            default_value=False,
                        ),
                    ),
                ],
                required_keys=["use_short"],
            ),
            "printable": True,
            "load_inv": True,
            "sorter": hint.ident,
            "paint": lambda row: _paint_host_inventory_attribute(row, hint),
            "export_for_python": lambda row, cell: _compute_attribute_painter_data(row, hint),
            "export_for_csv": lambda row, cell: (
                "" if (data := _compute_attribute_painter_data(row, hint)) is None else str(data)
            ),
            "export_for_json": lambda row, cell: _compute_attribute_painter_data(row, hint),
        },
    )

    # Declare sorter. It will detect numbers automatically
    _register_sorter(
        ident=hint.ident,
        long_inventory_title=long_inventory_title,
        load_inv=True,
        columns=["host_inventory", "host_structured_status"],
        hint=hint,
        value_extractor=lambda row: row["host_inventory"].get_attribute(hint.path, hint.key),
    )

    # Declare filter. Sync this with _register_table_column()
    filter_registry.register(hint.make_filter())


def _get_attributes(row: Row, path: SDPath) -> ImmutableAttributes | None:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return None
    return row.get("host_inventory", ImmutableTree()).get_tree(path).attributes


def _compute_attribute_painter_data(row: Row, hint: AttributeDisplayHint) -> SDValue:
    if (attributes := _get_attributes(row, hint.path)) is None:
        return None
    return attributes.pairs.get(hint.key)


def _paint_host_inventory_attribute(row: Row, hint: AttributeDisplayHint) -> CellSpec:
    if (attributes := _get_attributes(row, hint.path)) is None:
        return "", ""
    return compute_cell_spec(
        SDItem(
            hint.key,
            attributes.pairs.get(hint.key),
            attributes.retentions.get(hint.key),
        ),
        hint,
    )


def _paint_host_inventory_column(row: Row, hint: ColumnDisplayHint) -> CellSpec:
    if hint.ident not in row:
        return "", ""
    return compute_cell_spec(
        SDItem(
            SDKey(hint.ident),
            row[hint.ident],
            row.get("_".join([hint.ident, "retention_interval"])),
        ),
        hint,
    )


def _register_table_column(hint: ColumnDisplayHint) -> None:
    long_inventory_title = hint.long_inventory_title

    # TODO
    # - Sync this with _register_attribute_column()
    filter_registry.register(hint.make_filter())

    register_painter(
        hint.ident,
        {
            "title": long_inventory_title,
            # The short titles (used in column headers) may overlap for different painters, e.g.:
            # - BIOS > Version
            # - Firmware > Version
            # We want to keep column titles short, yet, to make up for overlapping we show the
            # long_title in the column title tooltips
            "short": hint.short_title,
            "tooltip_title": hint.long_title,
            "columns": [hint.ident],
            "paint": lambda row: _paint_host_inventory_column(row, hint),
            "sorter": hint.ident,
            # See views/painter/v0/base.py::Cell.painter_parameters
            # We have to add a dummy value here such that the painter_parameters are not None and
            # the "real" parameters, ie. _painter_params, are used.
            "params": FixedValue(PainterParameters(), totext=""),
        },
    )

    _register_sorter(
        ident=hint.ident,
        long_inventory_title=long_inventory_title,
        load_inv=False,
        columns=[hint.ident],
        hint=hint,
        value_extractor=lambda v: v.get(hint.ident),
    )


def _register_sorter(
    *,
    ident: str,
    long_inventory_title: str,
    load_inv: bool,
    columns: list[str],
    hint: AttributeDisplayHint | ColumnDisplayHint,
    value_extractor: Callable,
) -> None:
    register_sorter(
        ident,
        {
            "title": long_inventory_title,
            "columns": columns,
            "load_inv": load_inv,
            "cmp": lambda a, b: hint.sort_function(
                value_extractor(a),
                value_extractor(b),
            ),
        },
    )


def _register_table_view(node_hint: NodeDisplayHint) -> None:
    if not node_hint.table_view_name:
        return

    view_name = node_hint.table_view_name
    _register_info_class(
        view_name,
        node_hint.title,
        node_hint.title,
    )

    # Create the datasource (like a database view)
    data_source_registry.register(
        type(
            "DataSourceInventory%s" % node_hint.table_view_name.title(),
            (ABCDataSourceInventory,),
            {
                "_ident": view_name,
                "_inventory_path": inventory.InventoryPath(
                    path=node_hint.path, source=inventory.TreeSource.table
                ),
                "_title": node_hint.long_inventory_table_title,
                "_infos": ["host", view_name],
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
    for col_hint in node_hint.columns.values():
        # Declare a painter, sorter and filters for each path with display hint
        _register_table_column(col_hint)
        painters.append(ColumnSpec(col_hint.ident))
        filters.append(col_hint.ident)

    _register_views(
        view_name,
        node_hint.title,
        painters,
        filters,
        node_hint.path,
        node_hint.table_is_show_more,
        node_hint.icon,
    )


def _register_info_class(table_view_name: str, title_singular: str, title_plural: str) -> None:
    # Declare the "info" (like a database table)
    visual_info_registry.register(
        type(
            "VisualInfo%s" % table_view_name.title(),
            (VisualInfo,),
            {
                "_ident": table_view_name,
                "ident": property(lambda self: self._ident),
                "_title": title_singular,
                "title": property(lambda self: self._title),
                "_title_plural": title_plural,
                "title_plural": property(lambda self: self._title_plural),
                "single_spec": property(lambda self: []),
            },
        )
    )


def _register_views(
    table_view_name: str,
    title_plural: str,
    painters: Sequence[ColumnSpec],
    filters: Iterable[FilterName],
    path: SDPath,
    is_show_more: bool,
    icon: Icon | None,
) -> None:
    """Declare two views: one for searching globally. And one for the items of one host"""
    context: VisualContext = {f: {} for f in filters}

    # View for searching for items
    search_view_name = table_view_name + "_search"
    multisite_builtin_views[search_view_name] = {
        # General options
        "title": _l("Search %s") % title_plural.lower(),
        "description": _l("A view for searching in the inventory data for %s")
        % title_plural.lower(),
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
        "datasource": table_view_name,
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
        "is_show_more": is_show_more,
        "owner": UserId.builtin(),
        "add_context_to_title": True,
        "packaged": False,
        "megamenu_search_terms": [],
    }

    # View for the items of one host
    host_view_name = make_table_view_name_of_host(table_view_name)
    multisite_builtin_views[host_view_name] = {
        # General options
        "title": title_plural,
        "description": _l("A view for the %s of one host") % title_plural,
        "hidden": True,
        "hidebutton": False,
        "mustsearch": False,
        "link_from": {
            "single_infos": ["host"],
            "has_inventory_tree": path,
        },
        # Columns
        "painters": painters,
        # Filters
        "context": context,
        "icon": icon,
        "name": host_view_name,
        "single_infos": ["host"],
        "datasource": table_view_name,
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
        "is_show_more": is_show_more,
        "owner": UserId.builtin(),
        "add_context_to_title": True,
        "packaged": False,
        "megamenu_search_terms": [],
    }


# .
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

# .
#   .--history-------------------------------------------------------------.
#   |                   _     _     _                                      |
#   |                  | |__ (_)___| |_ ___  _ __ _   _                    |
#   |                  | '_ \| / __| __/ _ \| '__| | | |                   |
#   |                  | | | | \__ \ || (_) | |  | |_| |                   |
#   |                  |_| |_|_|___/\__\___/|_|   \__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


class PainterInvhistTime(Painter):
    @property
    def ident(self) -> str:
        return "invhist_time"

    def title(self, cell: Cell) -> str:
        return _("Inventory Date/Time")

    def short_title(self, cell: Cell) -> str:
        return _("Date/Time")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_time"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["invhist_time"],
            True,
            60 * 10,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterInvhistDelta(Painter):
    @property
    def ident(self) -> str:
        return "invhist_delta"

    def title(self, cell: Cell) -> str:
        return _("Inventory changes")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_delta", "invhist_time"]

    def _compute_data(self, row: Row, cell: Cell) -> ImmutableDeltaTree:
        try:
            _validate_inventory_tree_uniqueness(row)
        except MultipleInventoryTreesError:
            return ImmutableDeltaTree()

        return row.get("invhist_delta", ImmutableDeltaTree())

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if not (tree := self._compute_data(row, cell)):
            return "", ""

        tree_renderer = TreeRenderer(
            row["site"],
            row["host_name"],
            tree_id=str(row["invhist_time"]),
        )

        with output_funnel.plugged():
            tree_renderer.show(tree, self.request)
            code = HTML(output_funnel.drain())

        return "invtree", code

    def export_for_python(self, row: Row, cell: Cell) -> SDRawDeltaTree:
        return self._compute_data(row, cell).serialize()

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> SDRawDeltaTree:
        return self._compute_data(row, cell).serialize()


def _paint_invhist_count(row: Row, what: str) -> CellSpec:
    number = row["invhist_" + what]
    if number:
        return "narrow number", str(number)
    return "narrow number unused", "0"


class PainterInvhistRemoved(Painter):
    @property
    def ident(self) -> str:
        return "invhist_removed"

    def title(self, cell: Cell) -> str:
        return _("Removed entries")

    def short_title(self, cell: Cell) -> str:
        return _("Removed")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_removed"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_invhist_count(row, "removed")


class PainterInvhistNew(Painter):
    @property
    def ident(self) -> str:
        return "invhist_new"

    def title(self, cell: Cell) -> str:
        return _("New entries")

    def short_title(self, cell: Cell) -> str:
        return _("New")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_new"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_invhist_count(row, "new")


class PainterInvhistChanged(Painter):
    @property
    def ident(self) -> str:
        return "invhist_changed"

    def title(self, cell: Cell) -> str:
        return _("Changed entries")

    def short_title(self, cell: Cell) -> str:
        return _("Changed")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_changed"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_invhist_count(row, "changed")


# View for inventory history of one host

multisite_builtin_views["inv_host_history"] = {
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
