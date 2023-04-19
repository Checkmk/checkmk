#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import time
from collections import OrderedDict
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from functools import total_ordering
from typing import Any, Literal, NamedTuple, Protocol, TypeVar

from livestatus import LivestatusResponse, OnlySites, SiteId

import cmk.utils.defines as defines
import cmk.utils.render
from cmk.utils.structured_data import (
    Attributes,
    DeltaAttributes,
    DeltaStructuredDataNode,
    DeltaTable,
    RetentionIntervals,
    SDKey,
    SDKeyColumns,
    SDPath,
    SDRawDeltaTree,
    SDRow,
    SDValue,
    StructuredDataNode,
    Table,
)
from cmk.utils.type_defs import HostName, UserId

import cmk.gui.inventory as inventory
import cmk.gui.pages
import cmk.gui.sites as sites
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.plugins.visuals.inventory import (
    FilterInvBool,
    FilterInvFloat,
    FilterInvtableAdminStatus,
    FilterInvtableAvailable,
    FilterInvtableIDRange,
    FilterInvtableInterfaceType,
    FilterInvtableOperStatus,
    FilterInvtableText,
    FilterInvtableVersion,
    FilterInvText,
)
from cmk.gui.plugins.visuals.utils import (
    Filter,
    filter_registry,
    get_livestatus_filter_headers,
    get_ranged_table_filter_name,
    visual_info_registry,
    VisualInfo,
)
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
    VisualContext,
    VisualLinkSpec,
)
from cmk.gui.utils.escaping import escape_text
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import Checkbox, Dictionary, FixedValue, ValueSpec
from cmk.gui.view_utils import CellSpec, CSVExportError, render_labels
from cmk.gui.views.data_source import ABCDataSource, data_source_registry, RowTable
from cmk.gui.views.sorter import cmp_simple_number, declare_1to1_sorter, register_sorter
from cmk.gui.views.store import multisite_builtin_views

from ..painter.v0.base import Cell, Painter, painter_registry, register_painter
from ..painter_options import paint_age, painter_option_registry, PainterOption, PainterOptions
from . import builtin_display_hints
from .registry import inventory_displayhints, InventoryHintSpec

PaintResult = tuple[str, str | HTML]
PaintFunction = Callable[[Any], PaintResult]

_PAINT_FUNCTION_NAME_PREFIX = "inv_paint_"
_PAINT_FUNCTIONS: dict[str, PaintFunction] = {}


def register() -> None:
    builtin_display_hints.register(inventory_displayhints)


def update_paint_functions(mapping: Mapping[str, Any]) -> None:
    # Update paint functions from
    # 1. views (local web plugins are loaded including display hints and paint functions)
    # 2. here
    _PAINT_FUNCTIONS.update(
        {k: v for k, v in mapping.items() if k.startswith(_PAINT_FUNCTION_NAME_PREFIX)}
    )


def _get_paint_function_from_globals(paint_name: str) -> PaintFunction:
    # Do not overwrite local paint functions
    update_paint_functions({k: v for k, v in globals().items() if k not in _PAINT_FUNCTIONS})
    return _PAINT_FUNCTIONS[_PAINT_FUNCTION_NAME_PREFIX + paint_name]


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


@painter_option_registry.register
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


@painter_registry.register
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

    def _compute_data(self, row: Row, cell: Cell) -> StructuredDataNode | None:
        try:
            _validate_inventory_tree_uniqueness(row)
        except MultipleInventoryTreesError:
            return None

        return row.get("host_inventory")

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if not isinstance(tree := self._compute_data(row, cell), StructuredDataNode):
            return "", ""

        painter_options = PainterOptions.get_instance()
        tree_renderer = NodeRenderer(
            row["site"],
            row["host_name"],
            show_internal_tree_paths=painter_options.get("show_internal_tree_paths"),
        )

        with output_funnel.plugged():
            tree_renderer.show(tree, DISPLAY_HINTS.get_hints(tree.path))
            code = HTML(output_funnel.drain())

        return "invtree", code

    def export_for_python(self, row: Row, cell: Cell) -> dict | None:
        return (
            tree.serialize()
            if isinstance(tree := self._compute_data(row, cell), StructuredDataNode)
            else None
        )

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> dict | None:
        return (
            tree.serialize()
            if isinstance(tree := self._compute_data(row, cell), StructuredDataNode)
            else None
        )


class ABCRowTable(RowTable):
    def __init__(self, info_names, add_host_columns) -> None:  # type:ignore[no-untyped-def]
        super().__init__()
        self._info_names = info_names
        self._add_host_columns = add_host_columns

    def query(
        self,
        datasource: ABCDataSource,
        cells: Sequence[Cell],
        columns: Sequence[ColumnName],
        context: VisualContext,
        headers: str,
        only_sites: OnlySites,
        limit: object,
        all_active_filters: Sequence[Filter],
    ) -> tuple[Rows, int] | Rows:
        self._add_declaration_errors()

        # Create livestatus filter for filtering out hosts
        host_columns = (
            ["host_name"]
            + list({c for c in columns if c.startswith("host_") and c != "host_name"})
            + self._add_host_columns
        )

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
        headers = ["site"] + host_columns
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

    def _get_rows(self, hostrow: Row) -> Iterable[Row]:
        inv_data = self._get_inv_data(hostrow)
        return self._prepare_rows(inv_data)

    @abc.abstractmethod
    def _get_inv_data(self, hostrow: Row) -> Any:
        raise NotImplementedError()

    @abc.abstractmethod
    def _prepare_rows(self, inv_data: Any) -> Iterable[Row]:
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


def decorate_inv_paint(
    skip_painting_if_string: bool = False,
) -> Callable[[PaintFunction], PaintFunction]:
    def decorator(f: PaintFunction) -> PaintFunction:
        def wrapper(v: Any) -> PaintResult:
            if v in ["", None]:
                return "", ""
            if skip_painting_if_string and isinstance(v, str):
                return "number", v
            return f(v)

        return wrapper

    return decorator


@decorate_inv_paint()
def inv_paint_generic(v: str | float | int) -> PaintResult:
    if isinstance(v, float):
        return "number", "%.2f" % v
    if isinstance(v, int):
        return "number", "%d" % v
    return "", escape_text("%s" % v)


@decorate_inv_paint(skip_painting_if_string=True)
def inv_paint_hz(hz: float) -> PaintResult:
    return "number", cmk.utils.render.fmt_number_with_precision(hz, drop_zeroes=False, unit="Hz")


@decorate_inv_paint(skip_painting_if_string=True)
def inv_paint_bytes(b: int) -> PaintResult:
    if b == 0:
        return "number", "0"
    return "number", cmk.utils.render.fmt_bytes(b, precision=0)


@decorate_inv_paint(skip_painting_if_string=True)
def inv_paint_size(b: int) -> PaintResult:
    return "number", cmk.utils.render.fmt_bytes(b)


@decorate_inv_paint(skip_painting_if_string=True)
def inv_paint_bytes_rounded(b: int) -> PaintResult:
    if b == 0:
        return "number", "0"
    return "number", cmk.utils.render.fmt_bytes(b)


@decorate_inv_paint()
def inv_paint_number(b: str | int | float) -> PaintResult:
    return "number", str(b)


# Similar to paint_number, but is allowed to
# abbreviate things if numbers are very large
# (though it doesn't do so yet)
@decorate_inv_paint()
def inv_paint_count(b: str | int | float) -> PaintResult:
    return "number", str(b)


@decorate_inv_paint()
def inv_paint_nic_speed(bits_per_second: str) -> PaintResult:
    return "number", cmk.utils.render.fmt_nic_speed(bits_per_second)


@decorate_inv_paint()
def inv_paint_if_oper_status(oper_status: int) -> PaintResult:
    if oper_status == 1:
        css_class = "if_state_up"
    elif oper_status == 2:
        css_class = "if_state_down"
    else:
        css_class = "if_state_other"

    return "if_state " + css_class, defines.interface_oper_state_name(
        oper_status, "%s" % oper_status
    ).replace(" ", "&nbsp;")


# admin status can only be 1 or 2, matches oper status :-)
@decorate_inv_paint()
def inv_paint_if_admin_status(admin_status: int) -> PaintResult:
    return inv_paint_if_oper_status(admin_status)


@decorate_inv_paint()
def inv_paint_if_port_type(port_type: int) -> PaintResult:
    type_name = defines.interface_port_types().get(port_type, _("unknown"))
    return "", "%d - %s" % (port_type, type_name)


@decorate_inv_paint()
def inv_paint_if_available(available: bool) -> PaintResult:
    return "if_state " + (available and "if_available" or "if_not_available"), (
        available and _("free") or _("used")
    )


@decorate_inv_paint()
def inv_paint_mssql_is_clustered(clustered: bool) -> PaintResult:
    return "mssql_" + (clustered and "is_clustered" or "is_not_clustered"), (
        clustered and _("is clustered") or _("is not clustered")
    )


@decorate_inv_paint()
def inv_paint_mssql_node_names(node_names: str) -> PaintResult:
    return "", node_names


@decorate_inv_paint()
def inv_paint_ipv4_network(nw: str) -> PaintResult:
    if nw == "0.0.0.0/0":
        return "", _("Default")
    return "", nw


@decorate_inv_paint()
def inv_paint_ip_address_type(t: str) -> PaintResult:
    if t == "ipv4":
        return "", _("IPv4")
    if t == "ipv6":
        return "", _("IPv6")
    return "", t


@decorate_inv_paint()
def inv_paint_route_type(rt: str) -> PaintResult:
    if rt == "local":
        return "", _("Local route")
    return "", _("Gateway route")


@decorate_inv_paint(skip_painting_if_string=True)
def inv_paint_volt(volt: float) -> PaintResult:
    return "number", "%.1f V" % volt


@decorate_inv_paint(skip_painting_if_string=True)
def inv_paint_date(timestamp: int) -> PaintResult:
    date_painted = time.strftime("%Y-%m-%d", time.localtime(timestamp))
    return "number", "%s" % date_painted


@decorate_inv_paint(skip_painting_if_string=True)
def inv_paint_date_and_time(timestamp: int) -> PaintResult:
    date_painted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
    return "number", "%s" % date_painted


@decorate_inv_paint(skip_painting_if_string=True)
def inv_paint_age(age: float) -> PaintResult:
    return "number", cmk.utils.render.approx_age(age)


@decorate_inv_paint()
def inv_paint_bool(value: bool) -> PaintResult:
    return "", (_("Yes") if value else _("No"))


@decorate_inv_paint(skip_painting_if_string=True)
def inv_paint_timestamp_as_age(timestamp: int) -> PaintResult:
    age = time.time() - timestamp
    return inv_paint_age(age)


@decorate_inv_paint(skip_painting_if_string=True)
def inv_paint_timestamp_as_age_days(timestamp: int) -> PaintResult:
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
    change_day = round_to_day(timestamp)
    age_days = int((now_day - change_day) / 86400.0)

    css_class = "number"
    if age_days == 0:
        return css_class, _("today")
    if age_days == 1:
        return css_class, _("yesterday")
    return css_class, "%d %s ago" % (int(age_days), _("days"))


@decorate_inv_paint()
def inv_paint_csv_labels(csv_list: str) -> PaintResult:
    return "labels", HTMLWriter.render_br().join(csv_list.split(","))


@decorate_inv_paint()
def inv_paint_cmk_label(label: Sequence[str]) -> PaintResult:
    return "labels", render_labels(
        {label[0]: label[1]},
        object_type="host",
        with_links=True,
        label_sources={label[0]: "discovered"},
    )


@decorate_inv_paint()
def inv_paint_container_ready(ready: str) -> PaintResult:
    if ready == "yes":
        css_class = "if_state_up"
    elif ready == "no":
        css_class = "if_state_down"
    else:
        css_class = "if_state_other"

    return "if_state " + css_class, ready


@decorate_inv_paint()
def inv_paint_service_status(status: str) -> PaintResult:
    if status == "running":
        css_class = "if_state_up"
    elif status == "stopped":
        css_class = "if_state_down"
    else:
        css_class = "if_not_available"

    return "if_state " + css_class, status


# .
#   .--display hints-------------------------------------------------------.
#   |           _ _           _               _     _       _              |
#   |        __| (_)___ _ __ | | __ _ _   _  | |__ (_)_ __ | |_ ___        |
#   |       / _` | / __| '_ \| |/ _` | | | | | '_ \| | '_ \| __/ __|       |
#   |      | (_| | \__ \ |_) | | (_| | |_| | | | | | | | | | |_\__ \       |
#   |       \__,_|_|___/ .__/|_|\__,_|\__, | |_| |_|_|_| |_|\__|___/       |
#   |                  |_|            |___/                                |
#   '----------------------------------------------------------------------'

# TODO This protocol can also be used in cmk.utils.structured_data.py


class _Comparable(Protocol):
    @abc.abstractmethod
    def __eq__(self, other: object) -> bool:
        ...

    @abc.abstractmethod
    def __lt__(self, other: CmpInvValue) -> bool:
        ...

    @abc.abstractmethod
    def __gt__(self, other: CmpInvValue) -> bool:
        ...


CmpInvValue = TypeVar("CmpInvValue", bound=_Comparable)


def _get_paint_function(raw_hint: InventoryHintSpec) -> tuple[str, PaintFunction]:
    # FIXME At the moment  we need it to get tdclass: Clean this up one day.
    if "paint" in raw_hint:
        data_type = raw_hint["paint"]
        return data_type, _get_paint_function_from_globals(data_type)

    return "str", inv_paint_generic


SortFunction = Callable[[CmpInvValue, CmpInvValue], int]


def _make_sort_function(raw_hint: InventoryHintSpec) -> SortFunction:
    return _decorate_sort_function(raw_hint.get("sort", _cmp_inv_generic))


def _decorate_sort_function(sort_function: SortFunction) -> SortFunction:
    def wrapper(val_a: CmpInvValue | None, val_b: CmpInvValue | None) -> int:
        if val_a is None:
            return 0 if val_b is None else -1

        if val_b is None:
            return 0 if val_a is None else 1

        return sort_function(val_a, val_b)

    return wrapper


def _cmp_inv_generic(val_a: CmpInvValue, val_b: CmpInvValue) -> int:
    return (val_a > val_b) - (val_a < val_b)


def _make_title_function(raw_hint: InventoryHintSpec) -> Callable[[str], str]:
    if "title" not in raw_hint:
        return lambda word: word.replace("_", " ").title()

    if callable(title := raw_hint["title"]):
        # TODO Do we still need this?
        return title

    return lambda word: title


def _make_long_title_function(title: str, parent_path: SDPath) -> Callable[[], str]:
    return lambda: (
        DISPLAY_HINTS.get_hints(parent_path).node_hint.title + " ➤ " + title
        if parent_path
        else title
    )


def _make_long_inventory_title(
    long_title: str, *, node_type: Literal["node", "attribute", "table", "column"]
) -> str:
    # This long title with topic 'Inventory' is used for painters, sorters and filters.
    if node_type == "node":
        title_prefix = _("Inventory node")
    elif node_type == "attribute":
        title_prefix = _("Inventory attribute")
    elif node_type == "table":
        title_prefix = _("Inventory table")
    elif node_type == "column":
        title_prefix = _("Inventory column")
    else:
        raise ValueError(node_type)

    return f"{title_prefix}: {long_title}"


def _make_table_view_name_of_host(view_name: str) -> str:
    return f"{view_name}_of_host"


@dataclass(frozen=True)
class NodeDisplayHint:
    icon: str | None
    title: str
    _long_title_function: Callable[[], str]

    @property
    def long_title(self) -> str:
        return self._long_title_function()

    @property
    def long_inventory_title(self) -> str:
        return _make_long_inventory_title(self.long_title, node_type="node")

    @classmethod
    def from_raw(cls, path: SDPath, raw_hint: InventoryHintSpec) -> NodeDisplayHint:
        title = _make_title_function(raw_hint)(path[-1] if path else "")
        return cls(
            icon=raw_hint.get("icon"),
            title=title,
            _long_title_function=_make_long_title_function(title, path[:-1]),
        )


@dataclass(frozen=True)
class TableViewSpec:
    view_name: str
    title: str
    _long_title_function: Callable[[], str]
    icon: str | None

    @classmethod
    def from_raw(cls, path: SDPath, raw_hint: InventoryHintSpec) -> TableViewSpec | None:
        def _get_table_view_name(path: SDPath, raw_table_hint: InventoryHintSpec) -> str | None:
            if "view" not in raw_table_hint:
                return None
            if (view_name := raw_table_hint["view"]).endswith("_of_host"):
                return view_name[:-8]
            return view_name

        if "*" in path:
            # See DYNAMIC-PATHS
            return None

        if view_name := _get_table_view_name(path, raw_hint):
            title = raw_hint.get("title", "")
            return TableViewSpec(
                # This seems to be important for the availability of GUI elements, such as filters,
                # sorter, etc. in related contexts (eg. data source inv*).
                view_name=view_name if view_name.startswith("inv") else f"inv{view_name}",
                title=title,
                _long_title_function=_make_long_title_function(title, path[:-1]),
                icon=raw_hint.get("icon"),
            )

        return None

    @property
    def long_title(self) -> str:
        return self._long_title_function()

    @property
    def long_inventory_title(self) -> str:
        return _make_long_inventory_title(self.long_title, node_type="table")


KeyOrder = Sequence[str]


@dataclass(frozen=True)
class TableDisplayHint:
    key_order: KeyOrder
    is_show_more: bool
    view_spec: TableViewSpec | None = None

    @classmethod
    def from_raw(
        cls,
        path: SDPath,
        raw_hint: InventoryHintSpec,
        key_order: KeyOrder,
    ) -> TableDisplayHint:
        return cls(
            key_order=key_order,
            is_show_more=raw_hint.get("is_show_more", True),
            view_spec=TableViewSpec.from_raw(path, raw_hint),
        )


@dataclass(frozen=True)
class ColumnDisplayHint:
    title: str
    short: str | None
    _long_title_function: Callable[[], str]
    paint_function: PaintFunction
    sort_function: SortFunction
    filter_class: (
        None
        | type[FilterInvtableText]
        | type[FilterInvtableVersion]
        | type[FilterInvtableOperStatus]
        | type[FilterInvtableAdminStatus]
        | type[FilterInvtableAvailable]
        | type[FilterInvtableInterfaceType]
    )

    @property
    def long_title(self) -> str:
        return self._long_title_function()

    @property
    def long_inventory_title(self) -> str:
        return _make_long_inventory_title(self.long_title, node_type="column")

    @classmethod
    def from_raw(cls, path: SDPath, key: str, raw_hint: InventoryHintSpec) -> ColumnDisplayHint:
        _data_type, paint_function = _get_paint_function(raw_hint)
        title = _make_title_function(raw_hint)(key)
        return cls(
            title=title,
            short=raw_hint.get("short"),
            _long_title_function=_make_long_title_function(title, path),
            paint_function=paint_function,
            sort_function=_make_sort_function(raw_hint),
            filter_class=raw_hint.get("filter"),
        )

    def make_filter(
        self, table_view_name: str, ident: str
    ) -> (
        FilterInvtableText
        | FilterInvtableVersion
        | FilterInvtableOperStatus
        | FilterInvtableAdminStatus
        | FilterInvtableAvailable
        | FilterInvtableInterfaceType
        | FilterInvtableIDRange
    ):
        if self.filter_class:
            return self.filter_class(
                inv_info=table_view_name,
                ident=ident,
                title=self.long_inventory_title,
            )

        if (ranged_table_filter_name := get_ranged_table_filter_name(ident)) is not None:
            return FilterInvtableIDRange(
                inv_info=table_view_name,
                ident=ranged_table_filter_name,
                title=self.long_inventory_title,
            )

        return FilterInvtableText(
            inv_info=table_view_name,
            ident=ident,
            title=self.long_inventory_title,
        )


@dataclass(frozen=True)
class AttributesDisplayHint:
    key_order: KeyOrder

    @classmethod
    def from_raw(cls, key_order: KeyOrder) -> AttributesDisplayHint:
        return cls(key_order=key_order)


@dataclass(frozen=True)
class AttributeDisplayHint:
    title: str
    short: str | None
    _long_title_function: Callable[[], str]
    data_type: str
    paint_function: PaintFunction
    sort_function: SortFunction
    is_show_more: bool

    @property
    def long_title(self) -> str:
        return self._long_title_function()

    @property
    def long_inventory_title(self) -> str:
        return _make_long_inventory_title(self.long_title, node_type="attribute")

    @classmethod
    def from_raw(cls, path: SDPath, key: str, raw_hint: InventoryHintSpec) -> AttributeDisplayHint:
        data_type, paint_function = _get_paint_function(raw_hint)
        title = _make_title_function(raw_hint)(key)
        return cls(
            title=title,
            short=raw_hint.get("short"),
            _long_title_function=_make_long_title_function(title, path),
            data_type=data_type,
            paint_function=paint_function,
            sort_function=_make_sort_function(raw_hint),
            is_show_more=raw_hint.get("is_show_more", True),
        )

    def make_filter(
        self, ident: str, inventory_path: inventory.InventoryPath
    ) -> FilterInvText | FilterInvBool | FilterInvFloat:
        if self.data_type == "str":
            return FilterInvText(
                ident=ident,
                title=self.long_inventory_title,
                inventory_path=inventory_path,
                is_show_more=self.is_show_more,
            )

        if self.data_type == "bool":
            return FilterInvBool(
                ident=ident,
                title=self.long_inventory_title,
                inventory_path=inventory_path,
                is_show_more=self.is_show_more,
            )

        filter_info = _inv_filter_info().get(self.data_type, {})
        return FilterInvFloat(
            ident=ident,
            title=self.long_inventory_title,
            inventory_path=inventory_path,
            unit=filter_info.get("unit"),
            scale=filter_info.get("scale", 1.0),
            is_show_more=self.is_show_more,
        )


def _inv_filter_info():
    return {
        "bytes": {"unit": _("MB"), "scale": 1024 * 1024},
        "bytes_rounded": {"unit": _("MB"), "scale": 1024 * 1024},
        "hz": {"unit": _("MHz"), "scale": 1000000},
        "volt": {"unit": _("Volt")},
        "timestamp": {"unit": _("secs")},
    }


def inv_titleinfo_long(raw_path: str) -> str:
    """Return the titles of the last two path components of the node, e.g. "BIOS / Vendor"."""
    inventory_path = inventory.InventoryPath.parse(raw_path)
    hints = DISPLAY_HINTS.get_hints(inventory_path.path)

    if inventory_path.key:
        return hints.get_attribute_hint(inventory_path.key).long_title

    return hints.node_hint.long_title


@dataclass
class _RelatedRawHints:
    for_node: InventoryHintSpec = field(default_factory=dict)
    for_table: InventoryHintSpec = field(default_factory=dict)
    by_columns: dict[str, InventoryHintSpec] = field(default_factory=dict)
    by_attributes: dict[str, InventoryHintSpec] = field(default_factory=dict)


class _Column(NamedTuple):
    hint: ColumnDisplayHint
    key: str
    is_key_column: bool


class DisplayHints:
    def __init__(
        self,
        *,
        path: SDPath,
        node_hint: NodeDisplayHint,
        table_hint: TableDisplayHint,
        column_hints: OrderedDict[str, ColumnDisplayHint],
        attributes_hint: AttributesDisplayHint,
        attribute_hints: OrderedDict[str, AttributeDisplayHint],
    ) -> None:
        # This inventory path is an 'abc' path because it's the general, abstract path of a display
        # hint and may contain "*" (ie. placeholders).
        # Concrete paths (in trees) contain node names which are inserted into these placeholders
        # while calculating node titles.
        self.abc_path = path
        self.node_hint = node_hint
        self.table_hint = table_hint
        self.column_hints = column_hints
        self.attributes_hint = attributes_hint
        self.attribute_hints = attribute_hints

        self.nodes: dict[str, DisplayHints] = {}

    @classmethod
    def root(cls) -> DisplayHints:
        path: SDPath = tuple()
        return DisplayHints(
            path=path,
            node_hint=NodeDisplayHint.from_raw(path, {"title": _l("Inventory Tree")}),
            table_hint=TableDisplayHint.from_raw(path, {}, []),
            column_hints=OrderedDict({}),
            attributes_hint=AttributesDisplayHint.from_raw([]),
            attribute_hints=OrderedDict({}),
        )

    @classmethod
    def default(cls, path: SDPath) -> DisplayHints:
        return DisplayHints(
            path=path,
            node_hint=NodeDisplayHint.from_raw(path, {}),
            table_hint=TableDisplayHint.from_raw(path, {}, []),
            column_hints=OrderedDict({}),
            attributes_hint=AttributesDisplayHint.from_raw([]),
            attribute_hints=OrderedDict({}),
        )

    def parse(self, raw_hints: Mapping[str, InventoryHintSpec]) -> None:
        for path, related_raw_hints in sorted(self._get_related_raw_hints(raw_hints).items()):
            if not path:
                continue

            table_keys = self._complete_key_order(
                related_raw_hints.for_table.get("keyorder", []),
                set(related_raw_hints.by_columns),
            )

            attributes_keys = self._complete_key_order(
                related_raw_hints.for_node.get("keyorder", []),
                set(related_raw_hints.by_attributes),
            )

            self._get_parent(path).nodes.setdefault(
                path[-1],
                DisplayHints(
                    path=path,
                    # Some fields like 'title' or 'keyorder' of legacy display hints are declared
                    # either for
                    # - real nodes, eg. ".hardware.chassis.",
                    # - nodes with attributes, eg. ".hardware.cpu." or
                    # - nodes with a table, eg. ".software.packages:"
                    node_hint=NodeDisplayHint.from_raw(
                        path,
                        {**related_raw_hints.for_node, **related_raw_hints.for_table},
                    ),
                    table_hint=TableDisplayHint.from_raw(
                        path,
                        {**related_raw_hints.for_node, **related_raw_hints.for_table},
                        table_keys,
                    ),
                    column_hints=OrderedDict(
                        {
                            key: ColumnDisplayHint.from_raw(
                                path,
                                key,
                                related_raw_hints.by_columns.get(key, {}),
                            )
                            for key in table_keys
                        }
                    ),
                    attributes_hint=AttributesDisplayHint.from_raw(attributes_keys),
                    attribute_hints=OrderedDict(
                        {
                            key: AttributeDisplayHint.from_raw(
                                path,
                                key,
                                related_raw_hints.by_attributes.get(key, {}),
                            )
                            for key in attributes_keys
                        }
                    ),
                ),
            )

    @staticmethod
    def _get_related_raw_hints(
        raw_hints: Mapping[str, InventoryHintSpec]
    ) -> Mapping[SDPath, _RelatedRawHints]:
        related_raw_hints_by_path: dict[SDPath, _RelatedRawHints] = {}
        for raw_path, raw_hint in raw_hints.items():
            inventory_path = inventory.InventoryPath.parse(raw_path)
            related_raw_hints = related_raw_hints_by_path.setdefault(
                inventory_path.path,
                _RelatedRawHints(),
            )

            if inventory_path.source == inventory.TreeSource.node:
                related_raw_hints.for_node.update(raw_hint)
                continue

            if inventory_path.source == inventory.TreeSource.table:
                if inventory_path.key:
                    related_raw_hints.by_columns.setdefault(inventory_path.key, raw_hint)
                    continue

                related_raw_hints.for_table.update(raw_hint)
                continue

            if inventory_path.source == inventory.TreeSource.attributes and inventory_path.key:
                related_raw_hints.by_attributes.setdefault(inventory_path.key, raw_hint)
                continue

        return related_raw_hints_by_path

    @staticmethod
    def _complete_key_order(key_order: KeyOrder, additional_keys: set[str]) -> KeyOrder:
        return list(key_order) + [key for key in sorted(additional_keys) if key not in key_order]

    def _get_parent(self, path: SDPath) -> DisplayHints:
        node = self
        for node_name in path[:-1]:
            if node_name in node.nodes:
                node = node.nodes[node_name]
            else:
                node = node.nodes.setdefault(node_name, DisplayHints.default(path))

        return node

    def __iter__(self) -> Iterator[DisplayHints]:
        yield from self._make_inventory_paths_or_hints([])

    def _make_inventory_paths_or_hints(self, path: list[str]) -> Iterator[DisplayHints]:
        yield self
        for node_name, node in self.nodes.items():
            yield from node._make_inventory_paths_or_hints(path + [node_name])

    def get_hints(self, path: SDPath) -> DisplayHints:
        node = self
        for node_name in path:
            if node_name in node.nodes:
                node = node.nodes[node_name]

            elif "*" in node.nodes:
                node = node.nodes["*"]

            else:
                return DisplayHints.default(path)

        return node

    def get_column_hint(self, key: str) -> ColumnDisplayHint:
        if key in self.column_hints:
            return self.column_hints[key]
        return ColumnDisplayHint.from_raw(self.abc_path, key, {})

    def get_attribute_hint(self, key: str) -> AttributeDisplayHint:
        if key in self.attribute_hints:
            return self.attribute_hints[key]
        return AttributeDisplayHint.from_raw(self.abc_path, key, {})

    def make_columns(
        self, rows: Sequence[SDRow], key_columns: SDKeyColumns, path: SDPath
    ) -> Sequence[_Column]:
        sorting_keys = list(self.table_hint.key_order) + sorted(
            {k for r in rows for k in r} - set(self.table_hint.key_order)
        )
        return [_Column(self.get_column_hint(k), k, k in key_columns) for k in sorting_keys]

    @staticmethod
    def sort_rows(rows: Sequence[SDRow], columns: Sequence[_Column]) -> Sequence[SDRow]:
        # The sorting of rows is overly complicated here, because of the type SDValue = Any and
        # because the given values can be from both an inventory tree or from a delta tree.
        # Therefore, values may also be tuples of old and new value (delta tree), see _compare_dicts
        # in cmk.utils.structured_data.
        # TODO: Improve SDValue
        @total_ordering
        class _MinType:
            def __le__(self, other: object) -> bool:
                return True

            def __eq__(self, other: object) -> bool:
                return self is other

        min_type = _MinType()

        def _sanitize_value_for_sorting(
            value: SDValue,
        ) -> _MinType | SDValue | tuple[_MinType | SDValue, _MinType | SDValue]:
            # Replace None values with min_type to enable comparison for type SDValue, i.e. Any.
            if value is None:
                return min_type

            if isinstance(value, tuple):
                return (
                    min_type if value[0] is None else value[0],
                    min_type if value[1] is None else value[1],
                )

            return value

        return sorted(
            rows, key=lambda r: tuple(_sanitize_value_for_sorting(r.get(c.key)) for c in columns)
        )

    def sort_pairs(self, pairs: Mapping[SDKey, SDValue]) -> Sequence[tuple[SDKey, SDValue]]:
        sorting_keys = list(self.attributes_hint.key_order) + sorted(
            set(pairs) - set(self.attributes_hint.key_order)
        )
        return [(k, pairs[k]) for k in sorting_keys if k in pairs]

    def replace_placeholders(self, path: SDPath) -> str:
        if "%d" not in self.node_hint.title and "%s" not in self.node_hint.title:
            return self.node_hint.title

        title = self.node_hint.title.replace("%d", "%s")
        node_names = tuple(
            path[idx] for idx, node_name in enumerate(self.abc_path) if node_name == "*"
        )
        return title % node_names[-title.count("%s") :]


DISPLAY_HINTS = DisplayHints.root()


def register_table_views_and_columns() -> None:
    # Parse legacy display hints
    DISPLAY_HINTS.parse(inventory_displayhints)

    # Now register table views or columns (which need new display hints)
    _register_table_views_and_columns()


def _register_table_views_and_columns() -> None:
    # create painters for node with a display hint
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

        ident = ("inv",) + hints.abc_path

        _register_node_painter(
            inventory.InventoryPath(path=hints.abc_path, source=inventory.TreeSource.node),
            "_".join(ident),
            hints,
        )

        for key, attr_hint in hints.attribute_hints.items():
            _register_attribute_column(
                inventory.InventoryPath(
                    path=hints.abc_path, source=inventory.TreeSource.attributes, key=key
                ),
                "_".join(ident + (key,)),
                attr_hint,
            )

        _register_table_view(
            inventory.InventoryPath(path=hints.abc_path, source=inventory.TreeSource.table),
            hints,
        )


# .
#   .--columns-------------------------------------------------------------.
#   |                          _                                           |
#   |                 ___ ___ | |_   _ _ __ ___  _ __  ___                 |
#   |                / __/ _ \| | | | | '_ ` _ \| '_ \/ __|                |
#   |               | (_| (_) | | |_| | | | | | | | | \__ \                |
#   |                \___\___/|_|\__,_|_| |_| |_|_| |_|___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _register_node_painter(
    inventory_path: inventory.InventoryPath,
    name: str,
    hints: DisplayHints,
) -> None:
    """Declares painters for (sub) trees on all host related datasources."""
    register_painter(
        name,
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
            "sorter": name,
            "paint": lambda row: _paint_host_inventory_tree(row, inventory_path, hints),
            "export_for_python": lambda row, cell: _export_node_as_python_or_json(
                row, inventory_path
            ),
            "export_for_csv": lambda row, cell: _export_node_for_csv(),
            "export_for_json": lambda row, cell: _export_node_as_python_or_json(
                row, inventory_path
            ),
        },
    )


def _compute_node_painter_data(
    row: Row, inventory_path: inventory.InventoryPath
) -> StructuredDataNode | None:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return None

    if not isinstance(tree := row.get("host_inventory"), StructuredDataNode):
        return None

    return tree.get_node(inventory_path.path)


def _paint_host_inventory_tree(
    row: Row, inventory_path: inventory.InventoryPath, hints: DisplayHints
) -> CellSpec:
    if not (node := _compute_node_painter_data(row, inventory_path)):
        return "", ""

    painter_options = PainterOptions.get_instance()
    tree_renderer = NodeRenderer(
        row["site"],
        row["host_name"],
        show_internal_tree_paths=painter_options.get("show_internal_tree_paths"),
    )

    with output_funnel.plugged():
        tree_renderer.show(node, hints)
        code = HTML(output_funnel.drain())

    return "invtree", code


def _export_node_as_python(row: Row, inventory_path: inventory.InventoryPath) -> dict:
    return node.serialize() if (node := _compute_node_painter_data(row, inventory_path)) else {}


def _export_node_for_csv() -> str | HTML:
    raise CSVExportError()


def _export_node_as_python_or_json(row: Row, inventory_path: inventory.InventoryPath) -> dict:
    return node.serialize() if (node := _compute_node_painter_data(row, inventory_path)) else {}


def _register_attribute_column(
    inventory_path: inventory.InventoryPath,
    name: str,
    hint: AttributeDisplayHint,
) -> None:
    """Declares painters, sorters and filters to be used in views based on all host related
    datasources."""
    long_inventory_title = hint.long_inventory_title

    # Declare column painter
    register_painter(
        name,
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
            "sorter": name,
            "paint": lambda row: _paint_host_inventory_attribute(row, inventory_path, hint),
            "export_for_python": lambda row, cell: _export_attribute_as_python_or_json(
                row, inventory_path
            ),
            "export_for_csv": lambda row, cell: _export_attribute_for_csv(row, inventory_path),
            "export_for_json": lambda row, cell: _export_attribute_as_python_or_json(
                row, inventory_path
            ),
        },
    )

    # Declare sorter. It will detect numbers automatically
    _register_sorter(
        ident=name,
        long_inventory_title=long_inventory_title,
        load_inv=True,
        columns=["host_inventory", "host_structured_status"],
        hint=hint,
        value_extractor=lambda v: inventory.get_attribute(v["host_inventory"], inventory_path),
    )

    # Declare filter. Sync this with _register_table_column()
    filter_registry.register(hint.make_filter(name, inventory_path))


def _compute_attribute_painter_data(
    row: Row, inventory_path: inventory.InventoryPath
) -> None | str | int | float:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return None

    if not isinstance(tree := row.get("host_inventory"), StructuredDataNode):
        return None

    if (node := tree.get_node(inventory_path.path)) is None:
        return None

    if inventory_path.key in node.attributes.pairs:
        return node.attributes.pairs[inventory_path.key]

    return None


def _paint_host_inventory_attribute(
    row: Row, inventory_path: inventory.InventoryPath, hint: AttributeDisplayHint
) -> CellSpec:
    if (attribute_data := _compute_attribute_painter_data(row, inventory_path)) is None:
        return "", ""

    painter_options = PainterOptions.get_instance()
    tree_renderer = NodeRenderer(
        row["site"],
        row["host_name"],
        show_internal_tree_paths=painter_options.get("show_internal_tree_paths"),
    )

    with output_funnel.plugged():
        tree_renderer.show_attribute(attribute_data, hint)
        code = HTML(output_funnel.drain())

    return "", code


def _export_attribute_as_python(
    row: Row, inventory_path: inventory.InventoryPath
) -> None | str | int | float:
    return _compute_attribute_painter_data(row, inventory_path)


def _export_attribute_for_csv(row: Row, inventory_path: inventory.InventoryPath) -> str | HTML:
    return (
        "" if (data := _compute_attribute_painter_data(row, inventory_path)) is None else str(data)
    )


def _export_attribute_as_python_or_json(
    row: Row, inventory_path: inventory.InventoryPath
) -> None | str | int | float:
    return _compute_attribute_painter_data(row, inventory_path)


def _register_table_column(
    table_view_name: str,
    column: str,
    hint: ColumnDisplayHint,
) -> None:
    long_inventory_title = hint.long_inventory_title

    # TODO
    # - Sync this with _register_attribute_column()
    filter_registry.register(hint.make_filter(table_view_name, column))

    register_painter(
        column,
        {
            "title": long_inventory_title,
            # The short titles (used in column headers) may overlap for different painters, e.g.:
            # - BIOS > Version
            # - Firmware > Version
            # We want to keep column titles short, yet, to make up for overlapping we show the
            # long_title in the column title tooltips
            "short": hint.short or hint.title,
            "tooltip_title": hint.long_title,
            "columns": [column],
            "paint": lambda row: hint.paint_function(row.get(column)),
            "sorter": column,
            # See views/painter/v0/base.py::Cell.painter_parameters
            # We have to add a dummy value here such that the painter_parameters are not None and
            # the "real" parameters, ie. _painter_params, are used.
            "params": FixedValue(PainterParameters(), totext=""),
        },
    )

    _register_sorter(
        ident=column,
        long_inventory_title=long_inventory_title,
        load_inv=False,
        columns=[column],
        hint=hint,
        value_extractor=lambda v: v.get(column),
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

    def _get_inv_data(self, hostrow: Row) -> Sequence[SDRow]:
        try:
            merged_tree = inventory.load_filtered_and_merged_tree(hostrow)
        except inventory.LoadStructuredDataError:
            user_errors.add(
                MKUserError(
                    "load_inventory_tree",
                    _("Cannot load HW/SW inventory tree %s. Please remove the corrupted file.")
                    % inventory.get_short_inventory_filepath(hostrow.get("host_name", "")),
                )
            )
            return []

        if merged_tree is None:
            return []

        return _get_table_rows(merged_tree, self._inventory_path)

    def _prepare_rows(self, inv_data: Sequence[SDRow]) -> Iterable[Row]:
        return (
            [{info_name + "_" + key: value for key, value in row.items()} for row in inv_data]
            if self._info_names and (info_name := self._info_names[0])
            else []
        )


class ABCDataSourceInventory(ABCDataSource):
    @property
    def ignore_limit(self):
        return True

    @property
    @abc.abstractmethod
    def inventory_path(self) -> inventory.InventoryPath:
        raise NotImplementedError()


def _register_table_view(
    inventory_path: inventory.InventoryPath,
    hints: DisplayHints,
) -> None:
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
                "_inventory_path": inventory_path,
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
    for name, col_hint in hints.column_hints.items():
        column = table_view_spec.view_name + "_" + name

        # Declare a painter, sorter and filters for each path with display hint
        _register_table_column(
            table_view_spec.view_name,
            column,
            col_hint,
        )

        painters.append(ColumnSpec(column))
        filters.append(column)

    _register_views(
        table_view_spec.view_name,
        table_view_spec.title,
        painters,
        filters,
        [inventory_path],
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


def _register_views(
    table_view_name: str,
    title_plural: str,
    painters: Sequence[ColumnSpec],
    filters: Iterable[FilterName],
    inventory_paths: Sequence[inventory.InventoryPath],
    icon: Icon | None = None,
) -> None:
    """Declare two views: one for searching globally. And one for the items of one host"""
    is_show_more = True
    if len(inventory_paths) == 1:
        is_show_more = DISPLAY_HINTS.get_hints(inventory_paths[0].path).table_hint.is_show_more

    context: VisualContext = {f: {} for f in filters}

    # View for searching for items
    search_view_name = table_view_name + "_search"
    multisite_builtin_views[search_view_name] = {
        # General options
        "title": _l("Search %s") % title_plural,
        "description": _l("A view for searching in the inventory data for %s") % title_plural,
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
            "has_inventory_tree": [inventory_path.path for inventory_path in inventory_paths],
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
multisite_builtin_views["inv_host"] = {
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
        "has_inventory_tree": [inventory.InventoryPath.parse(".").path],
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
}

# View with table of all hosts, with some basic information
multisite_builtin_views["inv_hosts_cpu"] = {
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
}

# View with available and used ethernet ports
multisite_builtin_views["inv_hosts_ports"] = {
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
}

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

    def _get_inv_data(self, hostrow: Row) -> Sequence[inventory.HistoryEntry]:
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

        return history

    def _prepare_rows(self, inv_data: Sequence[inventory.HistoryEntry]) -> Iterable[Row]:
        for history_entry in inv_data:
            yield {
                "invhist_time": history_entry.timestamp,
                "invhist_delta": history_entry.delta_tree,
                "invhist_removed": history_entry.removed,
                "invhist_new": history_entry.new,
                "invhist_changed": history_entry.changed,
            }


@data_source_registry.register
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


@painter_registry.register
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
        return paint_age(row["invhist_time"], True, 60 * 10)


@painter_registry.register
class PainterInvhistDelta(Painter):
    @property
    def ident(self) -> str:
        return "invhist_delta"

    def title(self, cell: Cell) -> str:
        return _("Inventory changes")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_delta", "invhist_time"]

    def _compute_data(self, row: Row, cell: Cell) -> DeltaStructuredDataNode | None:
        try:
            _validate_inventory_tree_uniqueness(row)
        except MultipleInventoryTreesError:
            return None

        return row.get("invhist_delta")

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if not isinstance(tree := self._compute_data(row, cell), DeltaStructuredDataNode):
            return "", ""

        tree_renderer = DeltaNodeRenderer(
            row["site"],
            row["host_name"],
            tree_id="/" + str(row["invhist_time"]),
        )

        with output_funnel.plugged():
            tree_renderer.show(tree, DISPLAY_HINTS.get_hints(tree.path))
            code = HTML(output_funnel.drain())

        return "invtree", code

    def export_for_python(self, row: Row, cell: Cell) -> SDRawDeltaTree | None:
        return (
            tree.serialize()
            if isinstance(tree := self._compute_data(row, cell), DeltaStructuredDataNode)
            else None
        )

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> SDRawDeltaTree | None:
        return (
            tree.serialize()
            if isinstance(tree := self._compute_data(row, cell), DeltaStructuredDataNode)
            else None
        )


def _paint_invhist_count(row: Row, what: str) -> CellSpec:
    number = row["invhist_" + what]
    if number:
        return "narrow number", str(number)
    return "narrow number unused", "0"


@painter_registry.register
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


@painter_registry.register
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


@painter_registry.register
class PainterInvhistChanged(Painter):
    @property
    def ident(self) -> str:
        return "invhist_changed"

    def title(self, cell: Cell):  # type:ignore[no-untyped-def]
        return _("Changed entries")

    def short_title(self, cell: Cell) -> str:
        return _("Changed")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_changed"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_invhist_count(row, "changed")


# sorters
declare_1to1_sorter("invhist_time", cmp_simple_number, reverse=True)
declare_1to1_sorter("invhist_removed", cmp_simple_number)
declare_1to1_sorter("invhist_new", cmp_simple_number)
declare_1to1_sorter("invhist_changed", cmp_simple_number)

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
        "has_inventory_tree_history": [inventory.InventoryPath.parse(".").path],
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
}

# .
#   .--renderers-----------------------------------------------------------.
#   |                                _                                     |
#   |             _ __ ___ _ __   __| | ___ _ __ ___ _ __ ___              |
#   |            | '__/ _ \ '_ \ / _` |/ _ \ '__/ _ \ '__/ __|             |
#   |            | | |  __/ | | | (_| |  __/ | |  __/ |  \__ \             |
#   |            |_|  \___|_| |_|\__,_|\___|_|  \___|_|  |___/             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ABCNodeRenderer(abc.ABC):
    def __init__(
        self,
        site_id: SiteId,
        hostname: HostName,
        tree_id: str = "",
        show_internal_tree_paths: bool = False,
    ) -> None:
        self._site_id = site_id
        self._hostname = hostname
        self._tree_id = tree_id
        self._show_internal_tree_paths = show_internal_tree_paths

    def show(self, node: StructuredDataNode | DeltaStructuredDataNode, hints: DisplayHints) -> None:
        if not node.attributes.is_empty():
            self._show_attributes(node.attributes, hints)

        if not node.table.is_empty():
            self._show_table(node.table, hints)

        for child in sorted(node.nodes, key=lambda n: n.name):
            if isinstance(child, (StructuredDataNode, DeltaStructuredDataNode)):
                # sorted tries to find the common base class, which is object :(
                self._show_node(child)

    #   ---node-----------------------------------------------------------------

    def _show_node(self, node: StructuredDataNode | DeltaStructuredDataNode) -> None:
        raw_path = f".{'.'.join(map(str, node.path))}." if node.path else "."

        hints = DISPLAY_HINTS.get_hints(node.path)

        with foldable_container(
            treename=f"inv_{self._hostname}{self._tree_id}",
            id_=raw_path,
            isopen=False,
            title=self._get_header(
                hints.replace_placeholders(node.path),
                ".".join(map(str, node.path)),
            ),
            icon=hints.node_hint.icon,
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
                self.show(node, hints)

    #   ---table----------------------------------------------------------------

    def _show_table(self, table: Table | DeltaTable, hints: DisplayHints) -> None:
        if hints.table_hint.view_spec:
            # Link to Multisite view with exactly this table
            html.div(
                HTMLWriter.render_a(
                    _("Open this table for filtering / sorting"),
                    href=makeuri_contextless(
                        request,
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

        columns = hints.make_columns(table.rows, table.key_columns, table.path)

        # TODO: Use table.open_table() below.
        html.open_table(class_="data")
        html.open_tr()
        for column in columns:
            html.th(
                self._get_header(
                    column.hint.title,
                    "%s*" % column.key if column.is_key_column else column.key,
                )
            )
        html.close_tr()

        def _empty_or_equal(value: tuple[SDValue | None, SDValue | None] | SDValue | None) -> bool:
            # Some refactorings broke werk 6821. Especially delta trees may contain empty or
            # unchanged rows.
            if value is None:
                return True
            if isinstance(value, tuple) and len(value) == 2 and value[0] == value[1]:
                # Only applies to delta tree
                return True
            return False

        for row in hints.sort_rows(table.rows, columns):
            if all(_empty_or_equal(row.get(column.key)) for column in columns):
                continue

            html.open_tr(class_="even0")
            for column in columns:
                value = row.get(column.key)
                tdclass, _rendered_value = column.hint.paint_function(
                    value[1] if isinstance(value, tuple) else value
                )

                html.open_td(class_=tdclass)
                self._show_row_value(
                    value,
                    column.hint,
                    retention_intervals=(
                        None
                        if isinstance(table, DeltaTable)
                        else table.get_retention_intervals(column.key, row)
                    ),
                )
                html.close_td()
            html.close_tr()
        html.close_table()

    @abc.abstractmethod
    def _show_row_value(
        self,
        value: Any,
        col_hint: ColumnDisplayHint,
        retention_intervals: RetentionIntervals | None = None,
    ) -> None:
        raise NotImplementedError()

    #   ---attributes-----------------------------------------------------------

    def _show_attributes(
        self, attributes: Attributes | DeltaAttributes, hints: DisplayHints
    ) -> None:
        html.open_table()
        for key, value in hints.sort_pairs(attributes.pairs):
            attr_hint = hints.get_attribute_hint(key)

            html.open_tr()
            html.th(self._get_header(attr_hint.title, key))
            html.open_td()
            self.show_attribute(
                value,
                attr_hint,
                retention_intervals=(
                    None
                    if isinstance(attributes, DeltaAttributes)
                    else attributes.get_retention_intervals(key)
                ),
            )
            html.close_td()
            html.close_tr()
        html.close_table()

    @abc.abstractmethod
    def show_attribute(
        self,
        value: Any,
        attr_hint: AttributeDisplayHint,
        retention_intervals: RetentionIntervals | None = None,
    ) -> None:
        raise NotImplementedError()

    #   ---helper---------------------------------------------------------------

    def _get_header(self, title: str, key_info: str) -> HTML:
        header = HTML(title)
        if self._show_internal_tree_paths:
            header += " " + HTMLWriter.render_span("(%s)" % key_info, css="muted-text")
        return header

    def _show_child_value(
        self,
        value: Any,
        hint: ColumnDisplayHint | AttributeDisplayHint,
        retention_intervals: RetentionIntervals | None = None,
    ) -> None:
        if not isinstance(value, HTML):
            _tdclass, code = hint.paint_function(value)
            value = HTML(code)

        if self._is_outdated(retention_intervals):
            html.write_html(HTMLWriter.render_span(value.value, css="muted-text"))
        else:
            html.write_html(value)

    @staticmethod
    def _is_outdated(retention_intervals: RetentionIntervals | None) -> bool:
        return (
            False if retention_intervals is None else time.time() > retention_intervals.keep_until
        )


class NodeRenderer(ABCNodeRenderer):
    def _show_row_value(
        self,
        value: Any,
        col_hint: ColumnDisplayHint,
        retention_intervals: RetentionIntervals | None = None,
    ) -> None:
        self._show_child_value(value, col_hint, retention_intervals)

    def show_attribute(
        self,
        value: Any,
        attr_hint: AttributeDisplayHint,
        retention_intervals: RetentionIntervals | None = None,
    ) -> None:
        self._show_child_value(value, attr_hint, retention_intervals)


class DeltaNodeRenderer(ABCNodeRenderer):
    def _show_row_value(
        self,
        value: Any,
        col_hint: ColumnDisplayHint,
        retention_intervals: RetentionIntervals | None = None,
    ) -> None:
        self._show_delta_child_value(value, col_hint)

    def show_attribute(
        self,
        value: Any,
        attr_hint: AttributeDisplayHint,
        retention_intervals: RetentionIntervals | None = None,
    ) -> None:
        self._show_delta_child_value(value, attr_hint)

    def _show_delta_child_value(
        self,
        value: Any,
        hint: ColumnDisplayHint | AttributeDisplayHint,
    ) -> None:
        if value is None:
            value = (None, None)

        old, new = value
        if old is None and new is not None:
            html.open_span(class_="invnew")
            self._show_child_value(new, hint)
            html.close_span()
        elif old is not None and new is None:
            html.open_span(class_="invold")
            self._show_child_value(old, hint)
            html.close_span()
        elif old == new:
            self._show_child_value(old, hint)
        elif old is not None and new is not None:
            html.open_span(class_="invold")
            self._show_child_value(old, hint)
            html.close_span()
            html.write_text(" → ")
            html.open_span(class_="invnew")
            self._show_child_value(new, hint)
            html.close_span()


# Ajax call for fetching parts of the tree
@cmk.gui.pages.register("ajax_inv_render_tree")
def ajax_inv_render_tree() -> None:
    site_id = SiteId(request.get_ascii_input_mandatory("site"))
    hostname = HostName(request.get_ascii_input_mandatory("host"))
    inventory.verify_permission(hostname, site_id)

    raw_path = request.get_ascii_input_mandatory("raw_path")
    tree_id = request.get_ascii_input("tree_id", "")
    show_internal_tree_paths = bool(request.var("show_internal_tree_paths"))

    tree: StructuredDataNode | DeltaStructuredDataNode | None
    if tree_id:
        tree, corrupted_history_files = inventory.load_delta_tree(hostname, int(tree_id[1:]))
        if corrupted_history_files:
            user_errors.add(
                MKUserError(
                    "load_inventory_delta_tree",
                    _(
                        "Cannot load HW/SW inventory history entries %s. Please remove the corrupted files."
                    )
                    % ", ".join(corrupted_history_files),
                )
            )
            return
        tree_renderer: ABCNodeRenderer = DeltaNodeRenderer(
            site_id,
            hostname,
            tree_id=tree_id,
        )

    else:
        row = inventory.get_status_data_via_livestatus(site_id, hostname)
        try:
            tree = inventory.load_filtered_and_merged_tree(row)
        except inventory.LoadStructuredDataError:
            user_errors.add(
                MKUserError(
                    "load_inventory_tree",
                    _("Cannot load HW/SW inventory tree %s. Please remove the corrupted file.")
                    % inventory.get_short_inventory_filepath(hostname),
                )
            )
            return
        tree_renderer = NodeRenderer(
            site_id,
            hostname,
            show_internal_tree_paths=show_internal_tree_paths,
        )

    if tree is None:
        html.show_error(_("No such inventory tree."))
        return

    inventory_path = inventory.InventoryPath.parse(raw_path or "")
    if (node := tree.get_node(inventory_path.path)) is None:
        html.show_error(
            _("Invalid path in inventory tree: '%s' >> %s") % (raw_path, repr(inventory_path.path))
        )
        return

    tree_renderer.show(node, DISPLAY_HINTS.get_hints(node.path))


# .
#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def _get_table_rows(
    tree: StructuredDataNode, inventory_path: inventory.InventoryPath
) -> Sequence[SDRow]:
    return (
        []
        if inventory_path.source != inventory.TreeSource.table
        or (table := tree.get_table(inventory_path.path)) is None
        else table.rows
    )
