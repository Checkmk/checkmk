#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from __future__ import annotations

import abc
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from functools import total_ordering
from typing import NamedTuple

from livestatus import LivestatusResponse, OnlySites, SiteId

import cmk.utils.render
from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import (
    ImmutableAttributes,
    ImmutableDeltaAttributes,
    ImmutableDeltaTable,
    ImmutableDeltaTree,
    ImmutableTable,
    ImmutableTree,
    RetentionInterval,
    SDDeltaValue,
    SDKey,
    SDPath,
    SDRawDeltaTree,
    SDRawTree,
    SDRowIdent,
    SDValue,
)
from cmk.utils.user import UserId

import cmk.gui.inventory as inventory
import cmk.gui.sites as sites
from cmk.gui.config import active_config
from cmk.gui.data_source import ABCDataSource, data_source_registry, DataSourceRegistry, RowTable
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, Request
from cmk.gui.i18n import _, _l
from cmk.gui.ifaceoper import interface_oper_state_name, interface_port_types
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
    Rows,
    SingleInfos,
    SorterSpec,
    ViewName,
    ViewSpec,
    VisualContext,
    VisualLinkSpec,
)
from cmk.gui.utils.escaping import escape_text
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.theme import theme
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import Checkbox, Dictionary, FixedValue, ValueSpec
from cmk.gui.view_utils import CellSpec, CSVExportError
from cmk.gui.views.sorter import cmp_simple_number, declare_1to1_sorter, register_sorter
from cmk.gui.views.store import multisite_builtin_views
from cmk.gui.visuals import get_livestatus_filter_headers
from cmk.gui.visuals.filter import Filter, filter_registry
from cmk.gui.visuals.info import visual_info_registry, VisualInfo

from . import builtin_display_hints
from ._display_hints import (
    AttributeDisplayHint,
    ColumnDisplayHint,
    DISPLAY_HINTS,
    DisplayHints,
    PAINT_FUNCTION_NAME_PREFIX,
)
from .registry import (
    inv_paint_funtions,
    inventory_displayhints,
    InventoryHintSpec,
    InvPaintFunction,
    PaintResult,
)

__all__ = [
    "DISPLAY_HINTS",
    "DisplayHints",
    "InventoryHintSpec",
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
        {k: v for k, v in globals().items() if k not in inv_paint_funtions}
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


class ABCRowTable(RowTable):
    def __init__(self, info_names: Sequence[str], add_host_columns: Sequence[ColumnName]) -> None:
        super().__init__()
        self._info_names = info_names
        self._add_host_columns = add_host_columns

    def query(
        self,
        datasource: ABCDataSource,
        cells: Sequence[Cell],
        columns: Sequence[ColumnName],
        context: VisualContext,
        _unused_headers: str,
        only_sites: OnlySites,
        limit: object,
        all_active_filters: Sequence[Filter],
    ) -> tuple[Rows, int] | Rows:
        self._add_declaration_errors()

        # Create livestatus filter for filtering out hosts
        host_columns = [
            "host_name",
            *{c for c in columns if c.startswith("host_") and c != "host_name"},
            *self._add_host_columns,
        ]

        query = "GET hosts\n"
        query += "Columns: " + (" ".join(host_columns)) + "\n"

        query += "".join(get_livestatus_filter_headers(context, all_active_filters))

        if (
            active_config.debug_livestatus_queries
            and html.output_format == "html"
            and display_options.enabled(display_options.W)
        ):
            html.open_div(class_="livestatus message", onmouseover="this.style.display='none';")
            html.open_tt()
            html.write_text(query.replace("\n", "<br>\n"))
            html.close_tt()
            html.close_div()

        data = self._get_raw_data(only_sites, query)

        # Now create big table of all inventory entries of these hosts
        headers = ["site", *host_columns]
        rows = []
        for row in data:
            hostrow: Row = dict(zip(headers, row))
            for subrow in self._get_rows(hostrow):
                subrow.update(hostrow)
                rows.append(subrow)
        return rows, len(data)

    @staticmethod
    def _get_raw_data(only_sites: OnlySites, query: str) -> LivestatusResponse:
        with sites.only_sites(only_sites), sites.prepend_site():
            return sites.live().query(query)

    @abc.abstractmethod
    def _get_rows(self, hostrow: Row) -> Iterable[Row]:
        raise NotImplementedError()

    def _add_declaration_errors(self) -> None:
        pass


# .
#   .--paint helper--------------------------------------------------------.
#   |                   _       _     _          _                         |
#   |       _ __   __ _(_)_ __ | |_  | |__   ___| |_ __   ___ _ __         |
#   |      | '_ \ / _` | | '_ \| __| | '_ \ / _ \ | '_ \ / _ \ '__|        |
#   |      | |_) | (_| | | | | | |_  | | | |  __/ | |_) |  __/ |           |
#   |      | .__/ \__,_|_|_| |_|\__| |_| |_|\___|_| .__/ \___|_|           |
#   |      |_|                                    |_|                      |
#   '----------------------------------------------------------------------'


def inv_paint_generic(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, float):
        return "number", "%.2f" % value
    if isinstance(value, int):
        return "number", "%d" % value
    if isinstance(value, bool):
        return "", _("Yes") if value else _("No")
    return "", escape_text("%s" % value)


def inv_paint_hz(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, float):
        raise ValueError(value)
    return "number", cmk.utils.render.fmt_number_with_precision(value, drop_zeroes=False, unit="Hz")


def inv_paint_bytes(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int):
        raise ValueError(value)
    if value == 0:
        return "number", "0"
    return "number", cmk.utils.render.fmt_bytes(value, precision=0)


def inv_paint_size(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int):
        raise ValueError(value)
    return "number", cmk.utils.render.fmt_bytes(value)


def inv_paint_bytes_rounded(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int):
        raise ValueError(value)
    if value == 0:
        return "number", "0"
    return "number", cmk.utils.render.fmt_bytes(value)


def inv_paint_number(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, (str, int, float)):
        raise ValueError(value)
    return "number", str(value)


def inv_paint_count(value: SDValue) -> PaintResult:
    # Similar to paint_number, but is allowed to
    # abbreviate things if numbers are very large
    # (though it doesn't do so yet)
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, (str, int, float)):
        raise ValueError(value)
    return "number", str(value)


def inv_paint_nic_speed(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, (str, int)):
        raise ValueError(value)
    return "number", cmk.utils.render.fmt_nic_speed(value)


def inv_paint_if_oper_status(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, int):
        raise ValueError(value)
    if value == 1:
        css_class = "if_state_up"
    elif value == 2:
        css_class = "if_state_down"
    else:
        css_class = "if_state_other"

    return (
        "if_state " + css_class,
        interface_oper_state_name(value, "%s" % value).replace(" ", "&nbsp;"),
    )


def inv_paint_if_admin_status(value: SDValue) -> PaintResult:
    # admin status can only be 1 or 2, matches oper status :-)
    if value == "" or value is None:
        return "", ""
    return inv_paint_if_oper_status(value)


def inv_paint_if_port_type(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, int):
        raise ValueError(value)
    type_name = interface_port_types().get(value, _("unknown"))
    return "", "%d - %s" % (value, type_name)


def inv_paint_if_available(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, bool):
        raise ValueError(value)
    return (
        "if_state " + (value and "if_available" or "if_not_available"),
        (value and _("free") or _("used")),
    )


def inv_paint_mssql_is_clustered(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, bool):
        raise ValueError(value)
    return (
        "mssql_" + (value and "is_clustered" or "is_not_clustered"),
        (value and _("is clustered") or _("is not clustered")),
    )


def inv_paint_mssql_node_names(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    return "", value


def inv_paint_ipv4_network(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    if value == "0.0.0.0/0":
        return "", _("Default")
    return "", value


def inv_paint_ip_address_type(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    if value == "ipv4":
        return "", _("IPv4")
    if value == "ipv6":
        return "", _("IPv6")
    return "", value


def inv_paint_route_type(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    if value == "local":
        return "", _("Local route")
    return "", _("Gateway route")


def inv_paint_volt(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, float):
        raise ValueError(value)
    return "number", "%.1f V" % value


def inv_paint_date(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int):
        raise ValueError(value)
    date_painted = time.strftime("%Y-%m-%d", time.localtime(value))
    return "number", "%s" % date_painted


def inv_paint_date_and_time(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int):
        raise ValueError(value)
    date_painted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(value))
    return "number", "%s" % date_painted


def inv_paint_age(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, float):
        raise ValueError(value)
    return "number", cmk.utils.render.approx_age(value)


def inv_paint_bool(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, bool):
        raise ValueError(value)
    return "", (_("Yes") if value else _("No"))


def inv_paint_timestamp_as_age(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int):
        raise ValueError(value)
    return inv_paint_age(time.time() - value)


def inv_paint_timestamp_as_age_days(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if isinstance(value, str):
        return "number", value
    if not isinstance(value, int):
        raise ValueError(value)

    def round_to_day(ts):
        broken = time.localtime(ts)
        return int(
            time.mktime(
                (
                    broken.tm_year,
                    broken.tm_mon,
                    broken.tm_mday,
                    0,
                    0,
                    0,
                    broken.tm_wday,
                    broken.tm_yday,
                    broken.tm_isdst,
                )
            )
        )

    now_day = round_to_day(time.time())
    change_day = round_to_day(value)
    age_days = int((now_day - change_day) / 86400.0)

    css_class = "number"
    if age_days == 0:
        return css_class, _("today")
    if age_days == 1:
        return css_class, _("yesterday")
    return css_class, "%d %s ago" % (int(age_days), _("days"))


def inv_paint_csv_labels(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    return "labels", HTMLWriter.render_br().join(value.split(","))


def inv_paint_container_ready(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    if value == "yes":
        css_class = "if_state_up"
    elif value == "no":
        css_class = "if_state_down"
    else:
        css_class = "if_state_other"
    return "if_state " + css_class, value


def inv_paint_service_status(value: SDValue) -> PaintResult:
    if value == "" or value is None:
        return "", ""
    if not isinstance(value, str):
        raise ValueError(value)
    if value == "running":
        css_class = "if_state_up"
    elif value == "stopped":
        css_class = "if_state_down"
    else:
        css_class = "if_not_available"
    return "if_state " + css_class, value


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
    for hints in DISPLAY_HINTS:
        if "*" in hints.abc_path:
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

        _register_node_painter(hints, painter_options=painter_options)

        for key, attr_hint in hints.attribute_hints.items():
            _register_attribute_column(
                inventory.InventoryPath(
                    path=hints.abc_path,
                    source=inventory.TreeSource.attributes,
                    key=SDKey(key),
                ),
                attr_hint,
            )

        _register_table_view(hints)


def _register_node_painter(hints: DisplayHints, *, painter_options: PainterOptions) -> None:
    """Declares painters for (sub) trees on all host related datasources."""
    register_painter(
        hints.node_hint.ident,
        {
            "title": hints.node_hint.long_inventory_title,
            "short": hints.node_hint.title,
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
            "sorter": hints.node_hint.ident,
            "paint": lambda row: _paint_host_inventory_tree(
                row, hints.abc_path, painter_options=painter_options
            ),
            "export_for_python": lambda row, cell: (
                _compute_node_painter_data(row, hints.abc_path).serialize()
            ),
            "export_for_csv": lambda row, cell: _export_node_for_csv(),
            "export_for_json": lambda row, cell: (
                _compute_node_painter_data(row, hints.abc_path).serialize()
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


def _register_attribute_column(
    inventory_path: inventory.InventoryPath, hint: AttributeDisplayHint
) -> None:
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
            "short": hint.short or hint.title,
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
            "paint": lambda row: _paint_host_inventory_attribute(row, inventory_path, hint),
            "export_for_python": lambda row, cell: _compute_attribute_painter_data(
                row, inventory_path
            ),
            "export_for_csv": lambda row, cell: (
                ""
                if (data := _compute_attribute_painter_data(row, inventory_path)) is None
                else str(data)
            ),
            "export_for_json": lambda row, cell: _compute_attribute_painter_data(
                row, inventory_path
            ),
        },
    )

    # Declare sorter. It will detect numbers automatically
    _register_sorter(
        ident=hint.ident,
        long_inventory_title=long_inventory_title,
        load_inv=True,
        columns=["host_inventory", "host_structured_status"],
        hint=hint,
        value_extractor=lambda row: row["host_inventory"].get_attribute(
            inventory_path.path, inventory_path.key
        ),
    )

    # Declare filter. Sync this with _register_table_column()
    filter_registry.register(hint.make_filter(inventory_path))


def _get_attributes(row: Row, path: SDPath) -> ImmutableAttributes | None:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return None
    return row.get("host_inventory", ImmutableTree()).get_tree(path).attributes


def _compute_attribute_painter_data(row: Row, inventory_path: inventory.InventoryPath) -> SDValue:
    if (attributes := _get_attributes(row, inventory_path.path)) is None:
        return None
    return attributes.pairs.get(inventory_path.key)


def _paint_host_inventory_attribute(
    row: Row, inventory_path: inventory.InventoryPath, hint: AttributeDisplayHint
) -> CellSpec:
    if (attributes := _get_attributes(row, inventory_path.path)) is None:
        return "", ""
    return _compute_cell_spec(
        _SDItem(
            inventory_path.key,
            attributes.pairs.get(inventory_path.key),
            attributes.retentions.get(inventory_path.key),
        ),
        hint,
    )


def _paint_host_inventory_column(row: Row, hint: ColumnDisplayHint) -> CellSpec:
    if hint.ident not in row:
        return "", ""
    return _compute_cell_spec(
        _SDItem(
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
            "short": hint.short or hint.title,
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


class RowTableInventory(ABCRowTable):
    def __init__(self, info_name: str, inventory_path: inventory.InventoryPath) -> None:
        super().__init__([info_name], ["host_structured_status"])
        self._inventory_path = inventory_path

    def _get_rows(self, hostrow: Row) -> Iterable[Row]:
        if not (self._info_names and (info_name := self._info_names[0])):
            return

        try:
            table_rows = (
                inventory.load_filtered_and_merged_tree(hostrow)
                .get_tree(self._inventory_path.path)
                .table.rows_with_retentions
            )
        except inventory.LoadStructuredDataError:
            user_errors.add(
                MKUserError(
                    "load_inventory_tree",
                    _("Cannot load HW/SW inventory tree %s. Please remove the corrupted file.")
                    % inventory.get_short_inventory_filepath(hostrow.get("host_name", "")),
                )
            )
            return

        for table_row in table_rows:
            row: dict[str, int | float | str | bool | RetentionInterval | None] = {}
            for key, (value, retention_interval) in table_row.items():
                row["_".join([info_name, key])] = value
                row["_".join([info_name, key, "retention_interval"])] = retention_interval
            yield row


class ABCDataSourceInventory(ABCDataSource):
    @property
    def ignore_limit(self):
        return True

    @property
    @abc.abstractmethod
    def inventory_path(self) -> inventory.InventoryPath:
        raise NotImplementedError()


def _register_table_view(hints: DisplayHints) -> None:
    if (table_view_spec := hints.table_hint.view_spec) is None:
        return

    _register_info_class(
        table_view_spec.view_name,
        table_view_spec.title,
        table_view_spec.title,
    )

    # Create the datasource (like a database view)
    data_source_registry.register(
        type(
            "DataSourceInventory%s" % table_view_spec.view_name.title(),
            (ABCDataSourceInventory,),
            {
                "_ident": table_view_spec.view_name,
                "_inventory_path": inventory.InventoryPath(
                    path=hints.abc_path, source=inventory.TreeSource.table
                ),
                "_title": table_view_spec.long_inventory_title,
                "_infos": ["host", table_view_spec.view_name],
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
    for col_hint in hints.column_hints.values():
        # Declare a painter, sorter and filters for each path with display hint
        _register_table_column(col_hint)
        painters.append(ColumnSpec(col_hint.ident))
        filters.append(col_hint.ident)

    _register_views(
        table_view_spec.view_name,
        table_view_spec.title,
        painters,
        filters,
        hints.abc_path,
        hints.table_hint.is_show_more,
        table_view_spec.icon,
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


def _make_table_view_name_of_host(view_name: str) -> str:
    return f"{view_name}_of_host"


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
    host_view_name = _make_table_view_name_of_host(table_view_name)
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
                    name=_make_table_view_name_of_host("invinterface"),
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


class RowTableInventoryHistory(ABCRowTable):
    def __init__(self) -> None:
        super().__init__(["invhist"], [])
        self._inventory_path = None

    def _get_rows(self, hostrow: Row) -> Iterable[Row]:
        hostname: HostName = hostrow["host_name"]
        history, corrupted_history_files = inventory.get_history(hostname)
        if corrupted_history_files:
            user_errors.add(
                MKUserError(
                    "load_inventory_delta_tree",
                    _(
                        "Cannot load HW/SW inventory history entries %s. Please remove the corrupted files."
                    )
                    % ", ".join(sorted(corrupted_history_files)),
                )
            )
        for history_entry in history:
            yield {
                "invhist_time": history_entry.timestamp,
                "invhist_delta": history_entry.delta_tree,
                "invhist_removed": history_entry.removed,
                "invhist_new": history_entry.new,
                "invhist_changed": history_entry.changed,
            }


class DataSourceInventoryHistory(ABCDataSource):
    @property
    def ident(self) -> str:
        return "invhist"

    @property
    def title(self) -> str:
        return _("Inventory: History")

    @property
    def table(self) -> RowTable:
        return RowTableInventoryHistory()

    @property
    def infos(self) -> SingleInfos:
        return ["host", "invhist"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["host_name", "invhist_time"]


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

# .
#   .--tree renderer-------------------------------------------------------.
#   |     _                                      _                         |
#   |    | |_ _ __ ___  ___   _ __ ___ _ __   __| | ___ _ __ ___ _ __      |
#   |    | __| '__/ _ \/ _ \ | '__/ _ \ '_ \ / _` |/ _ \ '__/ _ \ '__|     |
#   |    | |_| | |  __/  __/ | | |  __/ | | | (_| |  __/ | |  __/ |        |
#   |     \__|_|  \___|\___| |_|  \___|_| |_|\__,_|\___|_|  \___|_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _make_columns(
    rows: Sequence[Mapping[SDKey, SDValue]] | Sequence[Mapping[SDKey, SDDeltaValue]],
    key_order: Sequence[SDKey],
) -> Sequence[SDKey]:
    return list(key_order) + sorted({k for r in rows for k in r} - set(key_order))


@total_ordering
class _MinType:
    def __le__(self, other: object) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        return self is other


class _SDItem(NamedTuple):
    key: SDKey
    value: SDValue
    retention_interval: RetentionInterval | None


def _sort_pairs(attributes: ImmutableAttributes, key_order: Sequence[SDKey]) -> Sequence[_SDItem]:
    sorted_keys = list(key_order) + sorted(set(attributes.pairs) - set(key_order))
    return [
        _SDItem(k, attributes.pairs[k], attributes.retentions.get(k))
        for k in sorted_keys
        if k in attributes.pairs
    ]


def _sort_rows(table: ImmutableTable, columns: Sequence[SDKey]) -> Sequence[Sequence[_SDItem]]:
    def _sort_row(
        ident: SDRowIdent, row: Mapping[SDKey, SDValue], columns: Sequence[SDKey]
    ) -> Sequence[_SDItem]:
        return [_SDItem(c, row.get(c), table.retentions.get(ident, {}).get(c)) for c in columns]

    min_type = _MinType()

    return [
        _sort_row(ident, row, columns)
        for ident, row in sorted(
            table.rows_by_ident.items(),
            key=lambda t: tuple(t[1].get(c) or min_type for c in columns),
        )
        if not all(v is None for v in row.values())
    ]


class _SDDeltaItem(NamedTuple):
    key: SDKey
    old: SDValue
    new: SDValue


def _sort_delta_pairs(
    attributes: ImmutableDeltaAttributes, key_order: Sequence[SDKey]
) -> Sequence[_SDDeltaItem]:
    sorted_keys = list(key_order) + sorted(set(attributes.pairs) - set(key_order))
    return [
        _SDDeltaItem(k, attributes.pairs[k].old, attributes.pairs[k].new)
        for k in sorted_keys
        if k in attributes.pairs
    ]


def _sort_delta_rows(
    table: ImmutableDeltaTable, columns: Sequence[SDKey]
) -> Sequence[Sequence[_SDDeltaItem]]:
    def _sort_row(
        row: Mapping[SDKey, SDDeltaValue], columns: Sequence[SDKey]
    ) -> Sequence[_SDDeltaItem]:
        return [
            _SDDeltaItem(c, v.old, v.new)
            for c in columns
            for v in (row.get(c) or SDDeltaValue(None, None),)
        ]

    min_type = _MinType()

    def _sanitize(value: SDDeltaValue) -> tuple[_MinType | SDValue, _MinType | SDValue]:
        return (value.old or min_type, value.new or min_type)

    return [
        _sort_row(row, columns)
        for row in sorted(
            table.rows,
            key=lambda r: tuple(_sanitize(r.get(c) or SDDeltaValue(None, None)) for c in columns),
        )
        if not all(left == right for left, right in row.values())
    ]


def _get_html_value(value: SDValue, hint: AttributeDisplayHint | ColumnDisplayHint) -> HTML:
    # TODO separate tdclass from rendered value
    _tdclass, code = hint.paint_function(value)
    return HTML(code)


def _compute_cell_spec(
    item: _SDItem,
    hint: AttributeDisplayHint | ColumnDisplayHint,
) -> tuple[str, HTML]:
    # TODO separate tdclass from rendered value
    tdclass, code = hint.paint_function(item.value)
    html_value = HTML(code)
    if (
        not html_value
        or item.retention_interval is None
        or item.retention_interval.source == "current"
    ):
        return tdclass, html_value

    now = int(time.time())
    valid_until = item.retention_interval.cached_at + item.retention_interval.cache_interval
    keep_until = valid_until + item.retention_interval.retention_interval
    if now > keep_until:
        return (
            tdclass,
            HTMLWriter.render_span(
                html_value
                + HTML("&nbsp;")
                + HTMLWriter.render_img(
                    theme.detect_icon_path("svc_problems", "icon_"),
                    class_=["icon"],
                ),
                title=_("Data is outdated and will be removed with the next check execution"),
                css=["muted_text"],
            ),
        )
    if now > valid_until:
        return (
            tdclass,
            HTMLWriter.render_span(
                html_value,
                title=_("Data was provided at %s and is considered valid until %s")
                % (
                    cmk.utils.render.date_and_time(item.retention_interval.cached_at),
                    cmk.utils.render.date_and_time(keep_until),
                ),
                css=["muted_text"],
            ),
        )
    return tdclass, html_value


def _show_item(
    item: _SDItem | _SDDeltaItem,
    hint: AttributeDisplayHint | ColumnDisplayHint,
) -> None:
    if isinstance(item, _SDDeltaItem):
        _show_delta_value(item, hint)
        return
    html.write_html(_compute_cell_spec(item, hint)[1])


def _show_delta_value(
    item: _SDDeltaItem,
    hint: AttributeDisplayHint | ColumnDisplayHint,
) -> None:
    if item.old is None and item.new is not None:
        html.open_span(class_="invnew")
        html.write_html(_get_html_value(item.new, hint))
        html.close_span()
    elif item.old is not None and item.new is None:
        html.open_span(class_="invold")
        html.write_html(_get_html_value(item.old, hint))
        html.close_span()
    elif item.old == item.new:
        html.write_html(_get_html_value(item.old, hint))
    elif item.old is not None and item.new is not None:
        html.open_span(class_="invold")
        html.write_html(_get_html_value(item.old, hint))
        html.close_span()
        html.write_text(" → ")
        html.open_span(class_="invnew")
        html.write_html(_get_html_value(item.new, hint))
        html.close_span()
    else:
        raise NotImplementedError()


class _LoadTreeError(Exception):
    pass


def _load_delta_tree(site_id: SiteId, host_name: HostName, tree_id: str) -> ImmutableDeltaTree:
    tree, corrupted_history_files = inventory.load_delta_tree(host_name, int(tree_id))
    if corrupted_history_files:
        user_errors.add(
            MKUserError(
                "load_inventory_delta_tree",
                _(
                    "Cannot load HW/SW inventory history entries %s."
                    " Please remove the corrupted files."
                )
                % ", ".join(corrupted_history_files),
            )
        )
        raise _LoadTreeError()
    return tree


def _load_inventory_tree(site_id: SiteId, host_name: HostName) -> ImmutableTree:
    row = inventory.get_status_data_via_livestatus(site_id, host_name)
    try:
        tree = inventory.load_filtered_and_merged_tree(row)
    except inventory.LoadStructuredDataError:
        user_errors.add(
            MKUserError(
                "load_inventory_tree",
                _("Cannot load HW/SW inventory tree %s. Please remove the corrupted file.")
                % inventory.get_short_inventory_filepath(host_name),
            )
        )
        raise _LoadTreeError()
    return tree


# Ajax call for fetching parts of the tree
def ajax_inv_render_tree() -> None:
    site_id = SiteId(request.get_ascii_input_mandatory("site"))
    host_name = request.get_validated_type_input_mandatory(HostName, "host")
    inventory.verify_permission(host_name, site_id)

    raw_path = request.get_ascii_input_mandatory("raw_path")
    show_internal_tree_paths = bool(request.var("show_internal_tree_paths"))
    tree_id = request.get_ascii_input_mandatory("tree_id", "")

    tree: ImmutableTree | ImmutableDeltaTree
    try:
        if tree_id:
            tree = _load_delta_tree(site_id, host_name, tree_id)
        else:
            tree = _load_inventory_tree(site_id, host_name)
    except _LoadTreeError:
        return

    inventory_path = inventory.InventoryPath.parse(raw_path or "")
    if not (tree := tree.get_tree(inventory_path.path)):
        html.show_error(_("No such tree below %r") % inventory_path.path)
        return

    TreeRenderer(site_id, host_name, show_internal_tree_paths, tree_id).show(tree, request)


class TreeRenderer:
    def __init__(
        self,
        site_id: SiteId,
        hostname: HostName,
        show_internal_tree_paths: bool = False,
        tree_id: str = "",
    ) -> None:
        self._site_id = site_id
        self._hostname = hostname
        self._show_internal_tree_paths = show_internal_tree_paths
        self._tree_id = tree_id
        self._tree_name = f"inv_{hostname}{tree_id}"

    def _get_header(self, title: str, key_info: str, icon: str | None = None) -> HTML:
        header = HTML(title)
        if self._show_internal_tree_paths:
            header += " " + HTMLWriter.render_span("(%s)" % key_info, css="muted_text")
        if icon:
            header += html.render_img(
                class_=(["title", "icon"]),
                src=theme.detect_icon_path(icon, "icon_"),
            )
        return header

    def _show_attributes(
        self, attributes: ImmutableAttributes | ImmutableDeltaAttributes, hints: DisplayHints
    ) -> None:
        sorted_pairs: Sequence[_SDItem] | Sequence[_SDDeltaItem]
        key_order = [SDKey(k) for k in hints.attributes_hint.key_order]
        if isinstance(attributes, ImmutableAttributes):
            sorted_pairs = _sort_pairs(attributes, key_order)
        else:
            sorted_pairs = _sort_delta_pairs(attributes, key_order)

        html.open_table()
        for item in sorted_pairs:
            attr_hint = hints.get_attribute_hint(item.key)
            html.open_tr()
            html.th(self._get_header(attr_hint.title, item.key))
            html.open_td()
            _show_item(item, attr_hint)
            html.close_td()
            html.close_tr()
        html.close_table()

    def _show_table(
        self, table: ImmutableTable | ImmutableDeltaTable, hints: DisplayHints, request_: Request
    ) -> None:
        if hints.table_hint.view_spec:
            # Link to Multisite view with exactly this table
            html.div(
                HTMLWriter.render_a(
                    _("Open this table for filtering / sorting"),
                    href=makeuri_contextless(
                        request_,
                        [
                            (
                                "view_name",
                                _make_table_view_name_of_host(hints.table_hint.view_spec.view_name),
                            ),
                            ("host", self._hostname),
                        ],
                        filename="view.py",
                    ),
                ),
                class_="invtablelink",
            )

        columns = _make_columns(table.rows, [SDKey(k) for k in hints.table_hint.key_order])
        sorted_rows: Sequence[Sequence[_SDItem]] | Sequence[Sequence[_SDDeltaItem]]
        if isinstance(table, ImmutableTable):
            sorted_rows = _sort_rows(table, columns)
        else:
            sorted_rows = _sort_delta_rows(table, columns)

        # TODO: Use table.open_table() below.
        html.open_table(class_="data")
        html.open_tr()
        for column in columns:
            html.th(
                self._get_header(
                    hints.get_column_hint(column).title,
                    "%s*" % column if column in table.key_columns else column,
                )
            )
        html.close_tr()

        for row in sorted_rows:
            html.open_tr(class_="even0")
            for item in row:
                column_hint = hints.get_column_hint(item.key)
                # TODO separate tdclass from rendered value
                if isinstance(item, _SDDeltaItem):
                    tdclass, _rendered_value = column_hint.paint_function(item.old or item.new)
                else:
                    tdclass, _rendered_value = column_hint.paint_function(item.value)
                html.open_td(class_=tdclass)
                _show_item(item, column_hint)
                html.close_td()
            html.close_tr()
        html.close_table()

    def _show_node(
        self, node: ImmutableTree | ImmutableDeltaTree, hints: DisplayHints, request_: Request
    ) -> None:
        raw_path = f".{'.'.join(map(str, node.path))}." if node.path else "."
        with foldable_container(
            treename=self._tree_name,
            id_=raw_path,
            isopen=False,
            title=self._get_header(
                hints.replace_placeholders(node.path),
                ".".join(map(str, node.path)),
                hints.node_hint.icon,
            ),
            fetch_url=makeuri_contextless(
                request,
                [
                    ("site", self._site_id),
                    ("host", self._hostname),
                    ("raw_path", raw_path),
                    ("show_internal_tree_paths", "on" if self._show_internal_tree_paths else ""),
                    ("tree_id", self._tree_id),
                ],
                "ajax_inv_render_tree.py",
            ),
        ) as is_open:
            if is_open:
                self.show(node, request_)

    def show(self, tree: ImmutableTree | ImmutableDeltaTree, request_: Request) -> None:
        hints = DISPLAY_HINTS.get_tree_hints(tree.path)

        if tree.attributes:
            self._show_attributes(tree.attributes, hints)

        if tree.table:
            self._show_table(tree.table, hints, request_)

        for name, node in sorted(tree.nodes_by_name.items(), key=lambda t: t[0]):
            if isinstance(node, (ImmutableTree, ImmutableDeltaTree)):
                # sorted tries to find the common base class, which is object :(
                self._show_node(node, hints.get_node_hints(name), request_)
