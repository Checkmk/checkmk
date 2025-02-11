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
    SDKey,
    SDNodeName,
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
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.ifaceoper import interface_oper_state_name, interface_port_types
from cmk.gui.inventory.filters import (
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
    get_ranged_table_filter_name,
)
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
from cmk.gui.view_utils import CellSpec, CSVExportError, render_labels
from cmk.gui.views.sorter import cmp_simple_number, declare_1to1_sorter, register_sorter
from cmk.gui.views.store import multisite_builtin_views
from cmk.gui.visuals import get_livestatus_filter_headers
from cmk.gui.visuals.filter import Filter, filter_registry
from cmk.gui.visuals.info import visual_info_registry, VisualInfo

from . import builtin_display_hints
from .registry import (
    inv_paint_funtions,
    inventory_displayhints,
    InventoryHintSpec,
    InvPaintFunction,
    PaintFunction,
    PaintResult,
)

_PAINT_FUNCTION_NAME_PREFIX = "inv_paint_"


def register_inv_paint_functions(mapping: Mapping[str, object]) -> None:
    for k, v in mapping.items():
        if k.startswith(_PAINT_FUNCTION_NAME_PREFIX) and callable(v):
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

        painter_options = PainterOptions.get_instance()
        tree_renderer = TreeRenderer(
            row["site"],
            row["host_name"],
            show_internal_tree_paths=painter_options.get("show_internal_tree_paths"),
        )

        with output_funnel.plugged():
            tree_renderer.show(tree)
            code = HTML(output_funnel.drain())

        return "invtree", code

    def export_for_python(self, row: Row, cell: Cell) -> SDRawTree:
        return self._compute_data(row, cell).serialize()

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> SDRawTree:
        return self._compute_data(row, cell).serialize()


class ABCRowTable(RowTable):
    def __init__(self, info_names, add_host_columns) -> None:  # type: ignore[no-untyped-def]
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
def inv_paint_generic(v: int | float | str | bool) -> PaintResult:
    if isinstance(v, float):
        return "number", "%.2f" % v
    if isinstance(v, int):
        return "number", "%d" % v
    if isinstance(v, bool):
        return "", _("Yes") if v else _("No")
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

    return "if_state " + css_class, interface_oper_state_name(
        oper_status, "%s" % oper_status
    ).replace(" ", "&nbsp;")


# admin status can only be 1 or 2, matches oper status :-)
@decorate_inv_paint()
def inv_paint_if_admin_status(admin_status: int) -> PaintResult:
    return inv_paint_if_oper_status(admin_status)


@decorate_inv_paint()
def inv_paint_if_port_type(port_type: int) -> PaintResult:
    type_name = interface_port_types().get(port_type, _("unknown"))
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
    return css_class, "%d %s" % (int(age_days), _("days ago"))


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
    def __eq__(self, other: object) -> bool: ...

    @abc.abstractmethod
    def __lt__(self, other: CmpInvValue) -> bool: ...

    @abc.abstractmethod
    def __gt__(self, other: CmpInvValue) -> bool: ...


CmpInvValue = TypeVar("CmpInvValue", bound=_Comparable)


def _get_paint_function(raw_hint: InventoryHintSpec) -> tuple[str, PaintFunction]:
    # FIXME At the moment  we need it to get tdclass: Clean this up one day.
    if "paint" in raw_hint:
        name = raw_hint["paint"]
        inv_paint_funtion = inv_paint_funtions[_PAINT_FUNCTION_NAME_PREFIX + name]
        return name, inv_paint_funtion["func"]

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
        DISPLAY_HINTS.get_tree_hints(parent_path).node_hint.title + " ➤ " + title
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
                view_name=(view_name if view_name.startswith("inv") else f"inv{view_name}"),
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
                title=self.long_title,
            )

        if (ranged_table_filter_name := get_ranged_table_filter_name(ident)) is not None:
            return FilterInvtableIDRange(
                inv_info=table_view_name,
                ident=ranged_table_filter_name,
                title=self.long_title,
            )

        return FilterInvtableText(
            inv_info=table_view_name,
            ident=ident,
            title=self.long_title,
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
                title=self.long_title,
                inventory_path=inventory_path,
                is_show_more=self.is_show_more,
            )

        if self.data_type == "bool":
            return FilterInvBool(
                ident=ident,
                title=self.long_title,
                inventory_path=inventory_path,
                is_show_more=self.is_show_more,
            )

        filter_info = _inv_filter_info().get(self.data_type, {})
        return FilterInvFloat(
            ident=ident,
            title=self.long_title,
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


@dataclass
class _RelatedRawHints:
    for_node: InventoryHintSpec = field(
        default_factory=lambda: InventoryHintSpec()  # pylint: disable=unnecessary-lambda
    )
    for_table: InventoryHintSpec = field(
        default_factory=lambda: InventoryHintSpec()  # pylint: disable=unnecessary-lambda
    )
    by_columns: dict[str, InventoryHintSpec] = field(default_factory=dict)
    by_attributes: dict[str, InventoryHintSpec] = field(default_factory=dict)


# TODO Workaround for InventoryHintSpec (TypedDict)
# https://github.com/python/mypy/issues/7178
_ALLOWED_KEYS: Sequence[
    Literal[
        "title",
        "short",
        "icon",
        "paint",
        "view",
        "keyorder",
        "sort",
        "filter",
        "is_show_more",
    ]
] = [
    "title",
    "short",
    "icon",
    "paint",
    "view",
    "keyorder",
    "sort",
    "filter",
    "is_show_more",
]


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

            node_or_table_hints = InventoryHintSpec()
            for key in _ALLOWED_KEYS:
                if (value := related_raw_hints.for_table.get(key)) is not None:
                    node_or_table_hints[key] = value
                elif (value := related_raw_hints.for_node.get(key)) is not None:
                    node_or_table_hints[key] = value

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
                    node_hint=NodeDisplayHint.from_raw(path, node_or_table_hints),
                    table_hint=TableDisplayHint.from_raw(path, node_or_table_hints, table_keys),
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
        raw_hints: Mapping[str, InventoryHintSpec],
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

    def get_attribute_hint(self, key: str) -> AttributeDisplayHint:
        return self.attribute_hints.get(key, AttributeDisplayHint.from_raw(self.abc_path, key, {}))

    def get_column_hint(self, key: str) -> ColumnDisplayHint:
        return self.column_hints.get(key, ColumnDisplayHint.from_raw(self.abc_path, key, {}))

    def get_node_hints(self, name: SDNodeName, path: SDPath) -> DisplayHints:
        return self.nodes.get(name, DisplayHints.default(path))

    def get_tree_hints(self, path: SDPath) -> DisplayHints:
        node = self
        for node_name in path:
            if node_name in node.nodes:
                node = node.nodes[node_name]

            elif "*" in node.nodes:
                node = node.nodes["*"]

            else:
                return DisplayHints.default(path)

        return node

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

        _register_node_painter("_".join(ident), hints)

        for key, attr_hint in hints.attribute_hints.items():
            _register_attribute_column("_".join(ident + (key,)), attr_hint, hints.abc_path, key)

        _register_table_view(hints)


# .
#   .--columns-------------------------------------------------------------.
#   |                          _                                           |
#   |                 ___ ___ | |_   _ _ __ ___  _ __  ___                 |
#   |                / __/ _ \| | | | | '_ ` _ \| '_ \/ __|                |
#   |               | (_| (_) | | |_| | | | | | | | | \__ \                |
#   |                \___\___/|_|\__,_|_| |_| |_|_| |_|___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _register_node_painter(name: str, hints: DisplayHints) -> None:
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
            "paint": lambda row: _paint_host_inventory_tree(row, hints.abc_path),
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


def _paint_host_inventory_tree(row: Row, path: SDPath) -> CellSpec:
    if not (tree := _compute_node_painter_data(row, path)):
        return "", ""

    painter_options = PainterOptions.get_instance()
    tree_renderer = TreeRenderer(
        row["site"],
        row["host_name"],
        show_internal_tree_paths=painter_options.get("show_internal_tree_paths"),
    )

    with output_funnel.plugged():
        tree_renderer.show(tree)
        code = HTML(output_funnel.drain())

    return "invtree", code


def _export_node_for_csv() -> str | HTML:
    raise CSVExportError()


def _register_attribute_column(
    name: str, hint: AttributeDisplayHint, path: SDPath, key: str
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
            "paint": lambda row: _paint_host_inventory_attribute(row, path, key, hint),
            "export_for_python": lambda row, cell: _compute_attribute_painter_data(row, path, key),
            "export_for_csv": lambda row, cell: (
                ""
                if (data := _compute_attribute_painter_data(row, path, key)) is None
                else str(data)
            ),
            "export_for_json": lambda row, cell: _compute_attribute_painter_data(row, path, key),
        },
    )

    inventory_path = inventory.InventoryPath(
        path=path,
        source=inventory.TreeSource.attributes,
        key=key,
    )

    # Declare sorter. It will detect numbers automatically
    _register_sorter(
        ident=name,
        long_inventory_title=long_inventory_title,
        load_inv=True,
        columns=["host_inventory", "host_structured_status"],
        hint=hint,
        value_extractor=lambda row: row["host_inventory"].get_attribute(
            inventory_path.path, inventory_path.key or ""
        ),
    )

    # Declare filter. Sync this with _register_table_column()
    filter_registry.register(hint.make_filter(name, inventory_path))


def _get_attributes(row: Row, path: SDPath) -> ImmutableAttributes | None:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return None
    return row.get("host_inventory", ImmutableTree()).get_tree(path).attributes


def _compute_attribute_painter_data(row: Row, path: SDPath, key: SDKey) -> SDValue:
    if (attributes := _get_attributes(row, path)) is None:
        return None
    return attributes.pairs.get(key)


def _paint_host_inventory_attribute(
    row: Row, path: SDPath, key: str, hint: AttributeDisplayHint
) -> CellSpec:
    if (attributes := _get_attributes(row, path)) is None:
        return "", ""
    return _compute_cell_spec(
        _InventoryTreeValueInfo(
            key,
            attributes.pairs.get(key),
            attributes.retentions.get(key),
        ),
        hint,
    )


def _paint_host_inventory_column(row: Row, column: str, hint: ColumnDisplayHint) -> CellSpec:
    if column not in row:
        return "", ""
    return _compute_cell_spec(
        _InventoryTreeValueInfo(
            column,
            row[column],
            row.get("_".join([column, "retention_interval"])),
        ),
        hint,
    )


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
            "paint": lambda row: _paint_host_inventory_column(row, column, hint),
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
        super().__init__([info_name], ["host_structured_status", "host_childs"])
        self._inventory_path = inventory_path

    def _get_inv_data(
        self, hostrow: Row
    ) -> Sequence[Mapping[SDKey, tuple[SDValue, RetentionInterval | None]]]:
        try:
            return (
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
            return []

    def _prepare_rows(
        self,
        inv_data: Sequence[Mapping[SDKey, tuple[SDValue, RetentionInterval | None]]],
    ) -> Iterable[Row]:
        if not (self._info_names and (info_name := self._info_names[0])):
            return []
        rows = []
        for inv_row in inv_data:
            row: dict[str, int | float | str | bool | RetentionInterval | None] = {}
            for key, (value, retention_interval) in inv_row.items():
                row["_".join([info_name, key])] = value
                row["_".join([info_name, key, "retention_interval"])] = retention_interval
            rows.append(row)
        return rows


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
        return paint_age(row["invhist_time"], True, 60 * 10)


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
            tree_renderer.show(tree)
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

    def title(self, cell: Cell):  # type: ignore[no-untyped-def]
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
    rows: (Sequence[Mapping[SDKey, SDValue]] | Sequence[Mapping[SDKey, tuple[SDValue, SDValue]]]),
    key_order: Sequence[SDKey],
) -> Sequence[SDKey]:
    return list(key_order) + sorted({k for r in rows for k in r} - set(key_order))


@total_ordering
class _MinType:
    def __le__(self, other: object) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        return self is other


class _InventoryTreeValueInfo(NamedTuple):
    key: SDKey
    value: SDValue
    retention_interval: RetentionInterval | None


def _sort_pairs(
    attributes: ImmutableAttributes, key_order: Sequence[SDKey]
) -> Sequence[_InventoryTreeValueInfo]:
    sorted_keys = list(key_order) + sorted(set(attributes.pairs) - set(key_order))
    return [
        _InventoryTreeValueInfo(k, attributes.pairs[k], attributes.retentions.get(k))
        for k in sorted_keys
        if k in attributes.pairs
    ]


def _sort_rows(
    table: ImmutableTable, columns: Sequence[SDKey]
) -> Sequence[Sequence[_InventoryTreeValueInfo]]:
    def _sort_row(
        ident: SDRowIdent, row: Mapping[SDKey, SDValue], columns: Sequence[SDKey]
    ) -> Sequence[_InventoryTreeValueInfo]:
        return [
            _InventoryTreeValueInfo(c, row.get(c), table.retentions.get(ident, {}).get(c))
            for c in columns
        ]

    min_type = _MinType()

    return [
        _sort_row(ident, row, columns)
        for ident, row in sorted(
            table.rows_by_ident.items(),
            key=lambda t: tuple(t[1].get(c) or min_type for c in columns),
        )
        if not all(v is None for v in row.values())
    ]


class _DeltaTreeValueInfo(NamedTuple):
    key: SDKey
    value: tuple[SDValue, SDValue]


def _sort_delta_pairs(
    attributes: ImmutableDeltaAttributes, key_order: Sequence[SDKey]
) -> Sequence[_DeltaTreeValueInfo]:
    sorted_keys = list(key_order) + sorted(set(attributes.pairs) - set(key_order))
    return [
        _DeltaTreeValueInfo(k, attributes.pairs[k]) for k in sorted_keys if k in attributes.pairs
    ]


def _sort_delta_rows(
    table: ImmutableDeltaTable, columns: Sequence[SDKey]
) -> Sequence[Sequence[_DeltaTreeValueInfo]]:
    def _sort_row(
        row: Mapping[SDKey, tuple[SDValue, SDValue]], columns: Sequence[SDKey]
    ) -> Sequence[_DeltaTreeValueInfo]:
        return [_DeltaTreeValueInfo(c, row.get(c) or (None, None)) for c in columns]

    min_type = _MinType()

    def _sanitize(
        value: tuple[SDValue, SDValue],
    ) -> tuple[_MinType | SDValue, _MinType | SDValue]:
        return (
            min_type if value[0] is None else value[0],
            min_type if value[1] is None else value[1],
        )

    return [
        _sort_row(row, columns)
        for row in sorted(
            table.rows,
            key=lambda r: tuple(_sanitize(r.get(c) or (None, None)) for c in columns),
        )
        if not all(left == right for left, right in row.values())
    ]


def _get_html_value(value: SDValue, hint: AttributeDisplayHint | ColumnDisplayHint) -> HTML:
    # TODO separate tdclass from rendered value
    _tdclass, code = hint.paint_function(value)
    return HTML() + code


def _compute_cell_spec(
    value_info: _InventoryTreeValueInfo,
    hint: AttributeDisplayHint | ColumnDisplayHint,
) -> tuple[str, HTML]:
    # TODO separate tdclass from rendered value
    tdclass, code = hint.paint_function(value_info.value)
    html_value = HTML() + code
    if (
        not html_value
        or value_info.retention_interval is None
        or value_info.retention_interval.source == "current"
    ):
        return tdclass, html_value

    now = int(time.time())
    valid_until = (
        value_info.retention_interval.cached_at + value_info.retention_interval.cache_interval
    )
    keep_until = valid_until + value_info.retention_interval.retention_interval
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
                    cmk.utils.render.date_and_time(value_info.retention_interval.cached_at),
                    cmk.utils.render.date_and_time(keep_until),
                ),
                css=["muted_text"],
            ),
        )
    return tdclass, html_value


def _show_value(
    value_info: _InventoryTreeValueInfo | _DeltaTreeValueInfo,
    hint: AttributeDisplayHint | ColumnDisplayHint,
) -> None:
    if isinstance(value_info, _DeltaTreeValueInfo):
        _show_delta_value(value_info.value, hint)
        return
    html.write_html(_compute_cell_spec(value_info, hint)[1])


def _show_delta_value(
    value: tuple[SDValue, SDValue],
    hint: AttributeDisplayHint | ColumnDisplayHint,
) -> None:
    old, new = value
    if old is None and new is not None:
        html.open_span(class_="invnew")
        html.write_html(_get_html_value(new, hint))
        html.close_span()
    elif old is not None and new is None:
        html.open_span(class_="invold")
        html.write_html(_get_html_value(old, hint))
        html.close_span()
    elif old == new:
        html.write_html(_get_html_value(old, hint))
    elif old is not None and new is not None:
        html.open_span(class_="invold")
        html.write_html(_get_html_value(old, hint))
        html.close_span()
        html.write_text(" → ")
        html.open_span(class_="invnew")
        html.write_html(_get_html_value(new, hint))
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

    TreeRenderer(site_id, host_name, show_internal_tree_paths, tree_id).show(tree)


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
        self,
        attributes: ImmutableAttributes | ImmutableDeltaAttributes,
        hints: DisplayHints,
    ) -> None:
        sorted_pairs: Sequence[_InventoryTreeValueInfo] | Sequence[_DeltaTreeValueInfo]
        if isinstance(attributes, ImmutableAttributes):
            sorted_pairs = _sort_pairs(attributes, hints.attributes_hint.key_order)
        else:
            sorted_pairs = _sort_delta_pairs(attributes, hints.attributes_hint.key_order)

        html.open_table()
        for value_info in sorted_pairs:
            attr_hint = hints.get_attribute_hint(value_info.key)
            html.open_tr()
            html.th(self._get_header(attr_hint.title, value_info.key))
            html.open_td()
            _show_value(value_info, attr_hint)
            html.close_td()
            html.close_tr()
        html.close_table()

    def _show_table(self, table: ImmutableTable | ImmutableDeltaTable, hints: DisplayHints) -> None:
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

        columns = _make_columns(table.rows, hints.table_hint.key_order)
        sorted_rows: (
            Sequence[Sequence[_InventoryTreeValueInfo]] | Sequence[Sequence[_DeltaTreeValueInfo]]
        )
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
            for value_info in row:
                column_hint = hints.get_column_hint(value_info.key)
                # TODO separate tdclass from rendered value
                if isinstance(value_info, _DeltaTreeValueInfo):
                    tdclass, _rendered_value = column_hint.paint_function(
                        value_info.value[0] or value_info.value[1]
                    )
                else:
                    tdclass, _rendered_value = column_hint.paint_function(value_info.value)
                html.open_td(class_=tdclass)
                _show_value(value_info, column_hint)
                html.close_td()
            html.close_tr()
        html.close_table()

    def _show_node(self, node: ImmutableTree | ImmutableDeltaTree, hints: DisplayHints) -> None:
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
                    (
                        "show_internal_tree_paths",
                        "on" if self._show_internal_tree_paths else "",
                    ),
                    ("tree_id", self._tree_id),
                ],
                "ajax_inv_render_tree.py",
            ),
        ) as is_open:
            if is_open:
                self.show(node)

    def show(self, tree: ImmutableTree | ImmutableDeltaTree) -> None:
        hints = DISPLAY_HINTS.get_tree_hints(tree.path)

        if tree.attributes:
            self._show_attributes(tree.attributes, hints)

        if tree.table:
            self._show_table(tree.table, hints)

        for name in sorted(tree.nodes_by_name):
            node = tree.nodes_by_name[name]
            self._show_node(node, hints.get_node_hints(name, node.path))
