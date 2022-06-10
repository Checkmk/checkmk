#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)

from livestatus import LivestatusResponse, OnlySites, SiteId

import cmk.utils.defines as defines
import cmk.utils.render
from cmk.utils.structured_data import (
    Attributes,
    RetentionIntervals,
    SDKey,
    SDKeyColumns,
    SDPath,
    SDRawPath,
    SDRow,
    SDValue,
    StructuredDataNode,
    Table,
)
from cmk.utils.type_defs import HostName

import cmk.gui.inventory as inventory
import cmk.gui.pages
import cmk.gui.sites as sites
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.plugins.views.utils import (
    ABCDataSource,
    Cell,
    cmp_simple_number,
    data_source_registry,
    declare_1to1_sorter,
    display_options,
    inventory_displayhints,
    InventoryHintSpec,
    multisite_builtin_views,
    paint_age,
    Painter,
    painter_option_registry,
    painter_registry,
    PainterOption,
    PainterOptions,
    register_painter,
    register_sorter,
    RowTable,
)
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
    filter_registry,
    get_livestatus_filter_headers,
    get_ranged_table,
    visual_info_registry,
    VisualInfo,
)
from cmk.gui.type_defs import ColumnName, FilterName, Icon, Row, Rows, SingleInfos
from cmk.gui.utils.escaping import escape_text
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import Checkbox, Dictionary, ValueSpec
from cmk.gui.view_utils import CellSpec, render_labels
from cmk.gui.views.builtin_views import host_view_filters

if TYPE_CHECKING:
    from cmk.gui.plugins.visuals.utils import Filter
    from cmk.gui.views import View


PaintResult = Tuple[str, Union[str, HTML]]
PaintFunction = Callable[[Any], PaintResult]


_PAINT_FUNCTION_NAME_PREFIX = "inv_paint_"
_PAINT_FUNCTIONS: dict[str, PaintFunction] = {}


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
    cache: Dict[HostName, List[SiteId]] = {}
    query_str = "GET hosts\nColumns: host_name\n"
    with sites.prepend_site():
        for row in sites.live().query(query_str):
            cache.setdefault(HostName(row[1]), []).append(SiteId(row[0]))
    return cache


def _cmp_inv_generic(val_a: object, val_b: object) -> int:
    if isinstance(val_a, (float, int)) and isinstance(val_b, (float, int)):
        return (val_a > val_b) - (val_a < val_b)

    if isinstance(val_a, str) and isinstance(val_b, str):
        return (val_a > val_b) - (val_a < val_b)

    raise TypeError(
        "Unsupported operand types for > and < (%s and %s)" % (type(val_a), type(val_b))
    )


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
        return _("Hardware & Software Tree")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_inventory", "host_structured_status"]

    @property
    def painter_options(self):
        return ["show_internal_tree_paths"]

    @property
    def load_inv(self):
        return True

    def render(self, row: Row, cell: Cell) -> CellSpec:
        try:
            _validate_inventory_tree_uniqueness(row)
        except MultipleInventoryTreesError:
            return "", ""

        tree = row.get("host_inventory")
        if tree is None:
            return "", ""

        assert isinstance(tree, StructuredDataNode)

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


class ABCRowTable(RowTable):
    def __init__(self, info_names, add_host_columns):
        super().__init__()
        self._info_names = info_names
        self._add_host_columns = add_host_columns

    def query(
        self,
        view: View,
        columns: List[ColumnName],
        headers: str,
        only_sites: OnlySites,
        limit,
        all_active_filters: List[Filter],
    ) -> Tuple[Rows, int]:
        self._add_declaration_errors()

        # Create livestatus filter for filtering out hosts
        host_columns = (
            ["host_name"]
            + list({c for c in columns if c.startswith("host_") and c != "host_name"})
            + self._add_host_columns
        )

        query = "GET hosts\n"
        query += "Columns: " + (" ".join(host_columns)) + "\n"

        query += "".join(get_livestatus_filter_headers(view.context, all_active_filters))

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

    def _get_raw_data(self, only_sites: OnlySites, query: str) -> LivestatusResponse:
        sites.live().set_only_sites(only_sites)
        sites.live().set_prepend_site(True)
        data = sites.live().query(query)
        sites.live().set_prepend_site(False)
        sites.live().set_only_sites(None)
        return data

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
def inv_paint_generic(v: Union[str, float, int]) -> PaintResult:
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
def inv_paint_number(b: Union[str, int, float]) -> PaintResult:
    return "number", str(b)


# Similar to paint_number, but is allowed to
# abbreviate things if numbers are very large
# (though it doesn't do so yet)
@decorate_inv_paint()
def inv_paint_count(b: Union[str, int, float]) -> PaintResult:
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
def inv_paint_cmk_label(label: List[str]) -> PaintResult:
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


def _get_paint_function(raw_hint: InventoryHintSpec) -> tuple[str, PaintFunction]:
    # FIXME At the moment  we need it to get tdclass: Clean this up one day.
    if "paint" in raw_hint:
        data_type = raw_hint["paint"]
        return data_type, _get_paint_function_from_globals(data_type)

    return "str", inv_paint_generic


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


@dataclass(frozen=True)
class NodeDisplayHint:
    icon: Optional[str]
    title: str
    short_title: str
    _long_title_function: Callable[[], str]

    @property
    def long_title(self) -> str:
        return self._long_title_function()

    @classmethod
    def make_from_hint(cls, path: SDPath, raw_hint: InventoryHintSpec) -> NodeDisplayHint:
        title = _make_title_function(raw_hint)(path[-1] if path else "")
        return cls(
            icon=raw_hint.get("icon"),
            title=title,
            short_title=raw_hint.get("short", title),
            _long_title_function=_make_long_title_function(title, path[:-1]),
        )


class Column(NamedTuple):
    hint: ColumnDisplayHint
    key: str
    is_key_column: bool


@dataclass(frozen=True)
class TableDisplayHint:
    key_order: Sequence[str]
    is_show_more: bool
    view_name: Optional[str]

    @classmethod
    def make_from_hint(cls, raw_hint: InventoryHintSpec) -> TableDisplayHint:
        return cls(
            key_order=raw_hint.get("keyorder", []),
            is_show_more=raw_hint.get("is_show_more", True),
            view_name=raw_hint.get("view"),
        )

    def make_columns(
        self, rows: Sequence[SDRow], key_columns: SDKeyColumns, path: SDPath
    ) -> Sequence[Column]:
        hints = DISPLAY_HINTS.get_hints(path)
        sorting_keys = list(self.key_order) + sorted(
            set(k for r in rows for k in r) - set(self.key_order)
        )
        return [Column(hints.get_column_hint(k), k, k in key_columns) for k in sorting_keys]

    def sort_rows(self, rows: Sequence[SDRow], columns: Sequence[Column]) -> Sequence[SDRow]:
        return sorted(rows, key=lambda r: tuple(r.get(c.key) or "" for c in columns))


@dataclass(frozen=True)
class ColumnDisplayHint:
    title: str
    short_title: str
    data_type: str
    paint_function: PaintFunction
    sort_function: Callable[[Any, Any], int]  # TODO improve type hints for args
    filter_class: (
        None
        | Type[FilterInvtableText]
        | Type[FilterInvtableVersion]
        | Type[FilterInvtableOperStatus]
        | Type[FilterInvtableAdminStatus]
        | Type[FilterInvtableAvailable]
        | Type[FilterInvtableInterfaceType]
    )

    @classmethod
    def make_from_hint(
        cls, path: SDPath, key: str, raw_hint: InventoryHintSpec
    ) -> ColumnDisplayHint:
        data_type, paint_function = _get_paint_function(raw_hint)
        title = _make_title_function(raw_hint)(key)
        return cls(
            title=title,
            short_title=raw_hint.get("short", title),
            data_type=data_type,
            paint_function=paint_function,
            sort_function=raw_hint.get("sort", _cmp_inv_generic),
            filter_class=raw_hint.get("filter"),
        )

    def make_filter(
        self, inv_info: str, ident: str, topic: str
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
                inv_info=inv_info,
                ident=ident,
                title=topic + ": " + self.title,
            )

        if (ranged_table := get_ranged_table(inv_info)) is not None:
            return FilterInvtableIDRange(
                inv_info=ranged_table,
                ident=ident,
                title=topic + ": " + self.title,
            )

        return FilterInvtableText(
            inv_info=inv_info,
            ident=ident,
            title=topic + ": " + self.title,
        )


@dataclass(frozen=True)
class AttributesDisplayHint:
    key_order: Sequence[str]

    @classmethod
    def make_from_hint(cls, raw_hint: InventoryHintSpec) -> AttributesDisplayHint:
        return cls(
            key_order=raw_hint.get("keyorder", []),
        )

    def sort_pairs(self, pairs: Mapping[SDKey, SDValue]) -> Sequence[Tuple[SDKey, SDValue]]:
        sorting_keys = list(self.key_order) + sorted(set(pairs) - set(self.key_order))
        return [(k, pairs[k]) for k in sorting_keys if k in pairs]


@dataclass(frozen=True)
class AttributeDisplayHint:
    title: str
    short_title: str
    _long_title_function: Callable[[], str]
    data_type: str
    paint_function: PaintFunction
    is_show_more: bool

    @property
    def long_title(self) -> str:
        return self._long_title_function()

    @classmethod
    def make_from_hint(
        cls, path: SDPath, key: str, raw_hint: InventoryHintSpec
    ) -> AttributeDisplayHint:
        data_type, paint_function = _get_paint_function(raw_hint)
        title = _make_title_function(raw_hint)(key)
        return cls(
            title=title,
            short_title=raw_hint.get("short", title),
            _long_title_function=_make_long_title_function(title, path),
            data_type=data_type,
            paint_function=paint_function,
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


def inv_titleinfo_long(raw_path: SDRawPath) -> str:
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
    by_columns: Dict[str, InventoryHintSpec] = field(default_factory=dict)
    by_attributes: Dict[str, InventoryHintSpec] = field(default_factory=dict)


class DisplayHints:
    def __init__(
        self,
        *,
        path: SDPath,
        node_hint: NodeDisplayHint,
        table_hint: TableDisplayHint,
        column_hints: Mapping[str, ColumnDisplayHint],
        attributes_hint: AttributesDisplayHint,
        attribute_hints: Mapping[str, AttributeDisplayHint],
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

        self.nodes: Dict[str, DisplayHints] = {}

    @classmethod
    def root(cls) -> DisplayHints:
        path: SDPath = tuple()
        return DisplayHints(
            path=path,
            node_hint=NodeDisplayHint.make_from_hint(path, {"title": _l("Inventory")}),
            table_hint=TableDisplayHint.make_from_hint({}),
            column_hints={},
            attributes_hint=AttributesDisplayHint.make_from_hint({}),
            attribute_hints={},
        )

    @classmethod
    def default(cls, path: SDPath) -> DisplayHints:
        return DisplayHints(
            path=path,
            node_hint=NodeDisplayHint.make_from_hint(path, {}),
            table_hint=TableDisplayHint.make_from_hint({}),
            column_hints={},
            attributes_hint=AttributesDisplayHint.make_from_hint({}),
            attribute_hints={},
        )

    def parse(self, raw_hints: Mapping[str, InventoryHintSpec]) -> None:
        for path, related_raw_hints in sorted(self._get_related_raw_hints(raw_hints).items()):
            if not path:
                continue

            self._get_parent(path).nodes.setdefault(
                path[-1],
                DisplayHints(
                    path=path,
                    # Some fields like 'title' or 'keyorder' of legacy display hints are declared
                    # either for
                    # - real nodes, eg. ".hardware.chassis.",
                    # - nodes with attributes, eg. ".hardware.cpu." or
                    # - nodes with a table, eg. ".software.packages:"
                    node_hint=NodeDisplayHint.make_from_hint(
                        path,
                        {**related_raw_hints.for_node, **related_raw_hints.for_table},
                    ),
                    table_hint=TableDisplayHint.make_from_hint(related_raw_hints.for_table),
                    column_hints={
                        key: ColumnDisplayHint.make_from_hint(path, key, raw_hint)
                        for key, raw_hint in related_raw_hints.by_columns.items()
                    },
                    attributes_hint=AttributesDisplayHint.make_from_hint(
                        related_raw_hints.for_node
                    ),
                    attribute_hints={
                        key: AttributeDisplayHint.make_from_hint(path, key, raw_hint)
                        for key, raw_hint in related_raw_hints.by_attributes.items()
                    },
                ),
            )

    @staticmethod
    def _get_related_raw_hints(
        raw_hints: Mapping[str, InventoryHintSpec]
    ) -> Mapping[SDPath, _RelatedRawHints]:
        related_raw_hints_by_path: Dict[SDPath, _RelatedRawHints] = {}
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

    def _make_inventory_paths_or_hints(self, path: List[str]) -> Iterator[DisplayHints]:
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
        return ColumnDisplayHint.make_from_hint(self.abc_path, key, {})

    def get_attribute_hint(self, key: str) -> AttributeDisplayHint:
        if key in self.attribute_hints:
            return self.attribute_hints[key]
        return AttributeDisplayHint.make_from_hint(self.abc_path, key, {})

    def replace_placeholders(self, path: SDPath) -> str:
        if "%d" not in self.node_hint.title and "%s" not in self.node_hint.title:
            return self.node_hint.title

        title = self.node_hint.title.replace("%d", "%s")
        node_names = tuple(
            path[idx] for idx, node_name in enumerate(self.abc_path) if node_name == "*"
        )
        return title % node_names[-title.count("%s") :]


DISPLAY_HINTS = DisplayHints.root()


def transform_legacy_display_hints():
    DISPLAY_HINTS.parse(inventory_displayhints)


# .
#   .--inventory columns---------------------------------------------------.
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   |                          _                                           |
#   |                 ___ ___ | |_   _ _ __ ___  _ __  ___                 |
#   |                / __/ _ \| | | | | '_ ` _ \| '_ \/ __|                |
#   |               | (_| (_) | | |_| | | | | | | | | \__ \                |
#   |                \___\___/|_|\__,_|_| |_| |_|_| |_|___/                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def declare_inventory_columns() -> None:
    # create painters for node with a display hint
    for hints in DISPLAY_HINTS:
        if "*" in hints.abc_path:
            continue

        ident = ("inv",) + hints.abc_path

        _declare_inv_column(
            inventory.InventoryPath(path=hints.abc_path, source=inventory.TreeSource.node),
            "_".join(ident),
            hints.node_hint,
        )

        for key, attr_hint in hints.attribute_hints.items():
            _declare_inv_column(
                inventory.InventoryPath(
                    path=hints.abc_path, source=inventory.TreeSource.attributes, key=key
                ),
                "_".join(ident + (key,)),
                attr_hint,
            )


def _declare_inv_column(
    inventory_path: inventory.InventoryPath,
    name: str,
    hint: NodeDisplayHint | AttributeDisplayHint,
) -> None:
    """Declares painters, sorters and filters to be used in views based on all host related
    datasources."""

    # Declare column painter
    painter_spec = {
        "title": (
            (_("Inventory") + ": " + hint.long_title)
            if inventory_path.path
            else _("Inventory Tree")
        ),
        "short": hint.short_title,
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
        "printable": isinstance(hint, AttributeDisplayHint),
        "load_inv": True,
        "paint": lambda row: _paint_host_inventory_tree(row, inventory_path),
        "sorter": name,
    }

    register_painter(name, painter_spec)

    # Sorters and Filters only for attributes
    if isinstance(hint, AttributeDisplayHint):
        # Declare sorter. It will detect numbers automatically
        register_sorter(
            name,
            {
                "_inventory_path": inventory_path,
                "title": _("Inventory") + ": " + hint.long_title,
                "columns": ["host_inventory", "host_structured_status"],
                "load_inv": True,
                "cmp": lambda self, a, b: _cmp_inventory_node(a, b, self._spec["_inventory_path"]),
            },
        )

        # Declare filter. Sync this with _declare_invtable_column()
        filter_registry.register(hint.make_filter(name, inventory_path))


def _cmp_inventory_node(
    a: Dict[str, StructuredDataNode],
    b: Dict[str, StructuredDataNode],
    inventory_path: inventory.InventoryPath,
) -> int:
    val_a = inventory.get_attribute(a["host_inventory"], inventory_path)
    val_b = inventory.get_attribute(b["host_inventory"], inventory_path)
    return _decorate_sort_func(_cmp_inv_generic)(val_a, val_b)


def _paint_host_inventory_tree(row: Row, inventory_path: inventory.InventoryPath) -> CellSpec:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return "", ""

    tree = row.get("host_inventory")
    if tree is None:
        return "", ""

    assert isinstance(tree, StructuredDataNode)

    if (node := tree.get_node(inventory_path.path)) is None:
        return "", ""

    painter_options = PainterOptions.get_instance()
    tree_renderer = NodeRenderer(
        row["site"],
        row["host_name"],
        show_internal_tree_paths=painter_options.get("show_internal_tree_paths"),
    )
    hints = DISPLAY_HINTS.get_hints(node.path)

    td_class = ""
    with output_funnel.plugged():
        if inventory_path.source == inventory.TreeSource.node:
            tree_renderer.show(node, hints)
            td_class = "invtree"

        elif inventory_path.source == inventory.TreeSource.table:
            tree_renderer.show_table(node.table, hints)

        elif (
            inventory_path.source == inventory.TreeSource.attributes
            and inventory_path.key in node.attributes.pairs
        ):
            tree_renderer.show_attribute(
                node.attributes.pairs[inventory_path.key],
                hints.get_attribute_hint(inventory_path.key),
            )

        code = HTML(output_funnel.drain())

    return td_class, code


# .
#   .--Datasources---------------------------------------------------------.
#   |       ____        _                                                  |
#   |      |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___         |
#   |      | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|        |
#   |      | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \        |
#   |      |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Basic functions for creating datasources for for table-like infor-  |
#   |  mation like software packages or network interfaces. That way the   |
#   |  user can access inventory data just like normal Livestatus tables.  |
#   |  This is needed for inventory data that is organized in tables.      |
#   |  Data where there is one fixed path per host for an item (like the   |
#   |  number of CPU cores) no datasource is being needed. These are just  |
#   |  painters that are available in the hosts info.                      |
#   '----------------------------------------------------------------------'


def _inv_find_subtable_columns(
    inventory_path: inventory.InventoryPath,
) -> Sequence[Tuple[str, ColumnDisplayHint]]:
    """Find the name of all columns of an embedded table that have a display
    hint. Respects the order of the columns if one is specified in the
    display hint.

    Also use the names found in keyorder to get even more of the available columns."""
    hints = DISPLAY_HINTS.get_hints(inventory_path.path)

    # Create dict from column name to its order number in the list
    with_numbers = enumerate(hints.table_hint.key_order)
    swapped = [(t[1], t[0]) for t in with_numbers]
    order = dict(swapped)

    columns = dict(hints.column_hints)

    for key in hints.table_hint.key_order:
        if key not in columns:
            columns[key] = hints.get_column_hint(key)

    return sorted(columns.items(), key=lambda t: (order.get(t[0], 999), t[0]))


def _decorate_sort_func(f):
    def wrapper(val_a, val_b):
        if val_a is None:
            return 0 if val_b is None else -1

        if val_b is None:
            return 0 if val_a is None else 1

        return f(val_a, val_b)

    return wrapper


def _declare_invtable_column(
    infoname: str,
    topic: str,
    column: str,
    hint: ColumnDisplayHint,
) -> None:
    # TODO
    # - Sync this with _declare_inv_column()
    filter_registry.register(hint.make_filter(infoname, column, topic))

    register_painter(
        column,
        {
            "title": topic + ": " + hint.title,
            "short": hint.short_title,
            "columns": [column],
            "paint": lambda row: hint.paint_function(row.get(column)),
            "sorter": column,
        },
    )

    register_sorter(
        column,
        {
            "title": _("Inventory") + ": " + hint.title,
            "columns": [column],
            "cmp": lambda self, a, b: _decorate_sort_func(hint.sort_function)(
                a.get(column), b.get(column)
            ),
        },
    )


def _get_table_rows(
    tree: StructuredDataNode, inventory_path: inventory.InventoryPath
) -> Sequence[SDRow]:
    return (
        []
        if inventory_path.source != inventory.TreeSource.table
        or (table := tree.get_table(inventory_path.path)) is None
        else table.rows
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
        # TODO check: hopefully there's only a table as input arg
        info_name = self._info_names[0]
        entries = []
        for entry in inv_data:
            newrow: Row = {}
            for key, value in entry.items():
                newrow[info_name + "_" + key] = value
            entries.append(newrow)
        return entries


class ABCDataSourceInventory(ABCDataSource):
    @property
    def ignore_limit(self):
        return True

    @property
    @abc.abstractmethod
    def inventory_path(self) -> inventory.InventoryPath:
        raise NotImplementedError()


# One master function that does all
def declare_invtable_view(
    infoname: str,
    raw_path: SDRawPath,
    title_singular: str,
    title_plural: str,
    icon: Optional[Icon] = None,
) -> None:
    inventory_path = inventory.InventoryPath.parse(raw_path)

    _register_info_class(infoname, title_singular, title_plural)

    # Create the datasource (like a database view)
    ds_class = type(
        "DataSourceInventory%s" % infoname.title(),
        (ABCDataSourceInventory,),
        {
            "_ident": infoname,
            "_inventory_path": inventory_path,
            "_title": "%s: %s" % (_("Inventory"), title_plural),
            "_infos": ["host", infoname],
            "ident": property(lambda s: s._ident),
            "title": property(lambda s: s._title),
            "table": property(lambda s: RowTableInventory(s._ident, s._inventory_path)),
            "infos": property(lambda s: s._infos),
            "keys": property(lambda s: []),
            "id_keys": property(lambda s: []),
            "inventory_path": property(lambda s: s._inventory_path),
        },
    )
    data_source_registry.register(ds_class)

    painters: List[Tuple[str, str, str]] = []
    filters = []
    for name, col_hint in _inv_find_subtable_columns(inventory_path):
        column = infoname + "_" + name

        # Declare a painter, sorter and filters for each path with display hint
        _declare_invtable_column(
            infoname,
            title_singular,
            column,
            col_hint,
        )

        painters.append((column, "", ""))
        filters.append(column)

    _declare_views(infoname, title_plural, painters, filters, [inventory_path], icon)


class RowMultiTableInventory(ABCRowTable):
    def __init__(
        self,
        sources: List[Tuple[str, inventory.InventoryPath]],
        match_by: List[str],
        errors: List[str],
    ) -> None:
        super().__init__([infoname for infoname, _path in sources], ["host_structured_status"])
        self._sources = sources
        self._match_by = match_by
        self._errors = errors

    def _get_inv_data(self, hostrow: Row) -> Sequence[Tuple[str, Sequence[SDRow]]]:
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

        return [
            (info_name, _get_table_rows(merged_tree, inventory_path))
            for info_name, inventory_path in self._sources
        ]

    def _prepare_rows(self, inv_data: Sequence[Tuple[str, Sequence[SDRow]]]) -> Iterable[Row]:
        joined_rows: Dict[Tuple[str, ...], Dict] = {}
        for this_info_name, this_inv_data in inv_data:
            for entry in this_inv_data:
                inst = joined_rows.setdefault(tuple(entry[key] for key in self._match_by), {})
                inst.update({this_info_name + "_" + k: v for k, v in entry.items()})
        return [joined_rows[match_by_key] for match_by_key in sorted(joined_rows)]

    def _add_declaration_errors(self) -> None:
        if self._errors:
            user_errors.add(MKUserError("declare_invtable_view", ", ".join(self._errors)))


def declare_joined_inventory_table_view(
    tablename: str,
    title_singular: str,
    title_plural: str,
    tables: List[str],
    match_by: List[str],
) -> None:

    _register_info_class(tablename, title_singular, title_plural)

    info_names: List[str] = []
    inventory_paths: List[inventory.InventoryPath] = []
    titles: List[str] = []
    errors = []
    for this_tablename in tables:
        visual_info_class = visual_info_registry.get(this_tablename)
        data_source_class = data_source_registry.get(this_tablename)
        if data_source_class is None or visual_info_class is None:
            errors.append(
                "Missing declare_invtable_view for inventory table view '%s'" % this_tablename
            )
            continue

        assert issubclass(data_source_class, ABCDataSourceInventory)
        ds = data_source_class()
        info_names.append(ds.ident)
        inventory_paths.append(ds.inventory_path)
        titles.append(visual_info_class().title)

    # Create the datasource (like a database view)
    ds_class = type(
        "DataSourceInventory%s" % tablename.title(),
        (ABCDataSource,),
        {
            "_ident": tablename,
            "_sources": list(zip(info_names, inventory_paths)),
            "_match_by": match_by,
            "_errors": errors,
            "_title": "%s: %s" % (_("Inventory"), title_plural),
            "_infos": ["host"] + info_names,
            "ident": property(lambda s: s._ident),
            "title": property(lambda s: s._title),
            "table": property(lambda s: RowMultiTableInventory(s._sources, s._match_by, s._errors)),
            "infos": property(lambda s: s._infos),
            "keys": property(lambda s: []),
            "id_keys": property(lambda s: []),
        },
    )
    data_source_registry.register(ds_class)

    known_common_columns = set()
    painters: List[Tuple[str, str, str]] = []
    filters = []
    for this_inventory_path, this_infoname, this_title in zip(inventory_paths, info_names, titles):
        for name, col_hint in _inv_find_subtable_columns(this_inventory_path):
            if name in match_by:
                # Filter out duplicate common columns which are used to join tables
                if name in known_common_columns:
                    continue
                known_common_columns.add(name)

            column = this_infoname + "_" + name

            # Declare a painter, sorter and filters for each path with display hint
            _declare_invtable_column(
                this_infoname,
                this_title,
                column,
                col_hint,
            )

            painters.append((column, "", ""))
            filters.append(column)

    _declare_views(tablename, title_plural, painters, filters, inventory_paths)


def _register_info_class(infoname: str, title_singular: str, title_plural: str) -> None:
    # Declare the "info" (like a database table)
    info_class = type(
        "VisualInfo%s" % infoname.title(),
        (VisualInfo,),
        {
            "_ident": infoname,
            "ident": property(lambda self: self._ident),
            "_title": title_singular,
            "title": property(lambda self: self._title),
            "_title_plural": title_plural,
            "title_plural": property(lambda self: self._title_plural),
            "single_spec": property(lambda self: []),
        },
    )
    visual_info_registry.register(info_class)


def _declare_views(
    infoname: str,
    title_plural: str,
    painters: List[Tuple[str, str, str]],
    filters: List[FilterName],
    inventory_paths: Sequence[inventory.InventoryPath],
    icon: Optional[Icon] = None,
) -> None:
    is_show_more = True
    if len(inventory_paths) == 1:
        is_show_more = DISPLAY_HINTS.get_hints(inventory_paths[0].path).table_hint.is_show_more

    # Declare two views: one for searching globally. And one
    # for the items of one host.
    view_spec = {
        "datasource": infoname,
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
    }

    # View for searching for items
    multisite_builtin_views[infoname + "_search"] = {
        # General options
        "title": _("Search %s") % title_plural,
        "description": _("A view for searching in the inventory data for %s") % title_plural,
        "hidden": False,
        "mustsearch": True,
        # Columns
        "painters": [("host", "inv_host", "")] + painters,
        # Filters
        "show_filters": [
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
        + filters,
        "hide_filters": [],
        "hard_filters": [],
        "hard_filtervars": [],
    }
    multisite_builtin_views[infoname + "_search"].update(view_spec)

    # View for the items of one host
    multisite_builtin_views[infoname + "_of_host"] = {
        # General options
        "title": title_plural,
        "description": _("A view for the %s of one host") % title_plural,
        "hidden": True,
        "mustsearch": False,
        "link_from": {
            "single_infos": ["host"],
            "has_inventory_tree": inventory_paths,
        },
        # Columns
        "painters": painters,
        # Filters
        "show_filters": filters,
        "hard_filters": [],
        "hard_filtervars": [],
        "hide_filters": ["host"],
        "icon": icon,
    }
    multisite_builtin_views[infoname + "_of_host"].update(view_spec)


def declare_invtable_views() -> None:
    """Declare views for a couple of embedded tables"""
    declare_invtable_view(
        "invswpac",
        ".software.packages:",
        _("Software package"),
        _("Software packages"),
    )
    declare_invtable_view(
        "invinterface",
        ".networking.interfaces:",
        _("Network interface"),
        _("Network interfaces"),
        "networking",
    )

    declare_invtable_view(
        "invdockerimages",
        ".software.applications.docker.images:",
        _("Docker images"),
        _("Docker images"),
    )
    declare_invtable_view(
        "invdockercontainers",
        ".software.applications.docker.containers:",
        _("Docker containers"),
        _("Docker containers"),
    )

    declare_invtable_view(
        "invother",
        ".hardware.components.others:",
        _("Other entity"),
        _("Other entities"),
    )
    declare_invtable_view(
        "invunknown",
        ".hardware.components.unknowns:",
        _("Unknown entity"),
        _("Unknown entities"),
    )
    declare_invtable_view(
        "invchassis",
        ".hardware.components.chassis:",
        _("Chassis"),
        _("Chassis"),
    )
    declare_invtable_view(
        "invbackplane",
        ".hardware.components.backplanes:",
        _("Backplane"),
        _("Backplanes"),
    )
    declare_invtable_view(
        "invcmksites",
        ".software.applications.check_mk.sites:",
        _("Checkmk site"),
        _("Checkmk sites"),
        "checkmk",
    )
    declare_invtable_view(
        "invcmkversions",
        ".software.applications.check_mk.versions:",
        _("Checkmk version"),
        _("Checkmk versions"),
        "checkmk",
    )
    declare_invtable_view(
        "invcontainer",
        ".hardware.components.containers:",
        _("HW container"),
        _("HW containers"),
    )
    declare_invtable_view(
        "invpsu",
        ".hardware.components.psus:",
        _("Power supply"),
        _("Power supplies"),
    )
    declare_invtable_view(
        "invfan",
        ".hardware.components.fans:",
        _("Fan"),
        _("Fans"),
    )
    declare_invtable_view(
        "invsensor",
        ".hardware.components.sensors:",
        _("Sensor"),
        _("Sensors"),
    )
    declare_invtable_view(
        "invmodule",
        ".hardware.components.modules:",
        _("Module"),
        _("Modules"),
    )
    declare_invtable_view(
        "invstack",
        ".hardware.components.stacks:",
        _("Stack"),
        _("Stacks"),
    )

    declare_invtable_view(
        "invorainstance",
        ".software.applications.oracle.instance:",
        _("Oracle instance"),
        _("Oracle instances"),
    )
    declare_invtable_view(
        "invorarecoveryarea",
        ".software.applications.oracle.recovery_area:",
        _("Oracle recovery area"),
        _("Oracle recovery areas"),
    )
    declare_invtable_view(
        "invoradataguardstats",
        ".software.applications.oracle.dataguard_stats:",
        _("Oracle dataguard statistic"),
        _("Oracle dataguard statistics"),
    )
    declare_invtable_view(
        "invoratablespace",
        ".software.applications.oracle.tablespaces:",
        _("Oracle tablespace"),
        _("Oracle tablespaces"),
    )
    declare_invtable_view(
        "invorasga",
        ".software.applications.oracle.sga:",
        _("Oracle SGA performance"),
        _("Oracle SGA performance"),
    )
    declare_invtable_view(
        "invorapga",
        ".software.applications.oracle.pga:",
        _("Oracle PGA performance"),
        _("Oracle PGA performance"),
    )
    declare_invtable_view(
        "invorasystemparameter",
        ".software.applications.oracle.systemparameter:",
        _("Oracle system parameter"),
        _("Oracle system parameters"),
    )
    declare_invtable_view(
        "invibmmqmanagers",
        ".software.applications.ibm_mq.managers:",
        _("Manager"),
        _("IBM MQ Managers"),
    )
    declare_invtable_view(
        "invibmmqchannels",
        ".software.applications.ibm_mq.channels:",
        _("Channel"),
        _("IBM MQ Channels"),
    )
    declare_invtable_view(
        "invibmmqqueues", ".software.applications.ibm_mq.queues:", _("Queue"), _("IBM MQ Queues")
    )
    declare_invtable_view(
        "invtunnels", ".networking.tunnels:", _("Networking Tunnels"), _("Networking Tunnels")
    )
    declare_invtable_view(
        "invkernelconfig",
        ".software.kernel_config:",
        _("Kernel configuration (sysctl)"),
        _("Kernel configurations (sysctl)"),
    )


# This would also be possible. But we muss a couple of display and filter hints.
# declare_invtable_view("invdisks",       ".hardware.storage.disks:",  _("Hard Disk"),          _("Hard Disks"))

# .
#   .--Views---------------------------------------------------------------.
#   |                    __     ___                                        |
#   |                    \ \   / (_) _____      _____                      |
#   |                     \ \ / /| |/ _ \ \ /\ / / __|                     |
#   |                      \ V / | |  __/\ V  V /\__ \                     |
#   |                       \_/  |_|\___| \_/\_/ |___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Special Multisite table views for software, ports, etc.             |
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
        "has_inventory_tree": [inventory.InventoryPath.parse(".")],
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
        ("host", "host", ""),
        ("inv", None, ""),
    ],
    # Filters
    "hard_filters": [],
    "hard_filtervars": [],
    # Previously (<2.0/1.6??) the hide_filters: ['host, 'site'] were needed to build the URL.
    # Now for creating the URL these filters are obsolete;
    # Side effect: with 'site' in hide_filters the only_sites filter for livestatus is NOT set
    # properly. Thus we removed 'site'.
    "hide_filters": ["host"],
    "show_filters": [],
    "sorters": [],
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
        ("host", "inv_host", ""),
        ("inv_software_os_name", None, ""),
        ("inv_hardware_cpu_cpus", None, ""),
        ("inv_hardware_cpu_cores", None, ""),
        ("inv_hardware_cpu_max_speed", None, ""),
        ("perfometer", None, "", "CPU load"),
        ("perfometer", None, "", "CPU utilization"),
    ],
    # Filters
    "hard_filters": ["has_inv"],
    "hard_filtervars": [("is_has_inv", "1")],
    "hide_filters": [],
    "show_filters": [
        "inv_hardware_cpu_cpus",
        "inv_hardware_cpu_cores",
        "inv_hardware_cpu_max_speed",
    ],
    "sorters": [],
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
        ("host", "invinterface_of_host", ""),
        ("inv_hardware_system_product", None, ""),
        ("inv_networking_total_interfaces", None, ""),
        ("inv_networking_total_ethernet_ports", None, ""),
        ("inv_networking_available_ethernet_ports", None, ""),
    ],
    # Filters
    "hard_filters": ["has_inv"],
    "hard_filtervars": [("is_has_inv", "1")],
    "hide_filters": [],
    "show_filters": host_view_filters + [],
    "sorters": [("inv_networking_available_ethernet_ports", True)],
}

# .
#   .--History-------------------------------------------------------------.
#   |                   _   _ _     _                                      |
#   |                  | | | (_)___| |_ ___  _ __ _   _                    |
#   |                  | |_| | / __| __/ _ \| '__| | | |                   |
#   |                  |  _  | \__ \ || (_) | |  | |_| |                   |
#   |                  |_| |_|_|___/\__\___/|_|   \__, |                   |
#   |                                             |___/                    |
#   +----------------------------------------------------------------------+
#   |  Code for history view of inventory                                  |
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
    def keys(self) -> List[ColumnName]:
        return []

    @property
    def id_keys(self) -> List[ColumnName]:
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
    def painter_options(self) -> List[str]:
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

    def render(self, row: Row, cell: Cell) -> CellSpec:
        try:
            _validate_inventory_tree_uniqueness(row)
        except MultipleInventoryTreesError:
            return "", ""

        tree = row.get("invhist_delta")
        if tree is None:
            return "", ""

        assert isinstance(tree, StructuredDataNode)

        tree_renderer = DeltaNodeRenderer(
            row["site"],
            row["host_name"],
            tree_id="/" + str(row["invhist_time"]),
        )

        with output_funnel.plugged():
            tree_renderer.show(tree, DISPLAY_HINTS.get_hints(tree.path))
            code = HTML(output_funnel.drain())

        return "invtree", code


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

    def title(self, cell: Cell):
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
        "has_inventory_tree_history": [inventory.InventoryPath.parse(".")],
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
        ("invhist_time", None, ""),
        ("invhist_removed", None, ""),
        ("invhist_new", None, ""),
        ("invhist_changed", None, ""),
        ("invhist_delta", None, ""),
    ],
    # Filters
    "hard_filters": [],
    "hard_filtervars": [],
    "hide_filters": ["host"],
    "show_filters": [],
    "sorters": [("invhist_time", False)],
}

# .
#   .--Node Renderer-------------------------------------------------------.
#   |  _   _           _        ____                _                      |
#   | | \ | | ___   __| | ___  |  _ \ ___ _ __   __| | ___ _ __ ___ _ __   |
#   | |  \| |/ _ \ / _` |/ _ \ | |_) / _ \ '_ \ / _` |/ _ \ '__/ _ \ '__|  |
#   | | |\  | (_) | (_| |  __/ |  _ <  __/ | | | (_| |  __/ | |  __/ |     |
#   | |_| \_|\___/ \__,_|\___| |_| \_\___|_| |_|\__,_|\___|_|  \___|_|     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# Just for compatibility
def render_inv_dicttable(*args):
    pass


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

    def show(self, node: StructuredDataNode, hints: DisplayHints) -> None:
        if not node.attributes.is_empty():
            self._show_attributes(node.attributes, hints)

        if not node.table.is_empty():
            self.show_table(node.table, hints)

        for the_node in sorted(node.nodes, key=lambda n: n.name):
            self._show_node(the_node)

    #   ---node-----------------------------------------------------------------

    def _show_node(self, node: StructuredDataNode) -> None:
        raw_path = f".{'.'.join(map(str, node.path))}." if node.path else "."

        hints = DISPLAY_HINTS.get_hints(node.path)

        with foldable_container(
            treename="inv_%s%s" % (self._hostname, self._tree_id),
            id_=raw_path,
            isopen=False,
            title=self._get_header(
                hints.replace_placeholders(node.path),
                ".".join(map(str, node.path)),
                "#666",
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

    def show_table(self, table: Table, hints: DisplayHints) -> None:
        if hints.table_hint.view_name:
            # Link to Multisite view with exactly this table
            html.div(
                HTMLWriter.render_a(
                    _("Open this table for filtering / sorting"),
                    href=makeuri_contextless(
                        request,
                        [
                            ("view_name", hints.table_hint.view_name),
                            ("host", self._hostname),
                        ],
                        filename="view.py",
                    ),
                ),
                class_="invtablelink",
            )

        columns = hints.table_hint.make_columns(table.rows, table.key_columns, table.path)

        # TODO: Use table.open_table() below.
        html.open_table(class_="data")
        html.open_tr()
        for column in columns:
            html.th(
                self._get_header(
                    column.hint.short_title,
                    column.key,
                    "#DDD",
                    is_key_column=column.is_key_column,
                )
            )
        html.close_tr()

        for row in hints.table_hint.sort_rows(table.rows, columns):
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
                    retention_intervals=table.get_retention_intervals(column.key, row),
                )
                html.close_td()
            html.close_tr()
        html.close_table()

    @abc.abstractmethod
    def _show_row_value(
        self,
        value: Any,
        col_hint: ColumnDisplayHint,
        retention_intervals: Optional[RetentionIntervals] = None,
    ) -> None:
        raise NotImplementedError()

    #   ---attributes-----------------------------------------------------------

    def _show_attributes(self, attributes: Attributes, hints: DisplayHints) -> None:
        html.open_table()
        for key, value in hints.attributes_hint.sort_pairs(attributes.pairs):
            attr_hint = hints.get_attribute_hint(key)

            html.open_tr()
            html.th(
                self._get_header(
                    attr_hint.title,
                    key,
                    "#DDD",
                )
            )
            html.open_td()
            self.show_attribute(
                value,
                attr_hint,
                retention_intervals=attributes.get_retention_intervals(key),
            )
            html.close_td()
            html.close_tr()
        html.close_table()

    @abc.abstractmethod
    def show_attribute(
        self,
        value: Any,
        attr_hint: AttributeDisplayHint,
        retention_intervals: Optional[RetentionIntervals] = None,
    ) -> None:
        raise NotImplementedError()

    #   ---helper---------------------------------------------------------------

    def _get_header(
        self,
        title: str,
        key: str,
        hex_color: str,
        *,
        is_key_column: bool = False,
    ) -> HTML:
        header = HTML(title)
        if self._show_internal_tree_paths:
            key_info = "%s*" % key if is_key_column else key
            header += " " + HTMLWriter.render_span("(%s)" % key_info, style="color: %s" % hex_color)
        return header

    def _show_child_value(
        self,
        value: Any,
        hint: Union[ColumnDisplayHint, AttributeDisplayHint],
        retention_intervals: Optional[RetentionIntervals] = None,
    ) -> None:
        if isinstance(value, HTML):
            html.write_html(value)
        else:
            _tdclass, code = hint.paint_function(value)
            html.write_text(code)

        if (ret_value_to_write := self._get_retention_value(retention_intervals)) is not None:
            html.write_html(ret_value_to_write)

    def _get_retention_value(
        self,
        retention_intervals: Optional[RetentionIntervals],
    ) -> Optional[HTML]:
        if retention_intervals is None:
            return None

        now = time.time()

        if now <= retention_intervals.valid_until:
            return None

        if now <= retention_intervals.keep_until:
            _tdclass, value = inv_paint_age(retention_intervals.keep_until - now)
            return HTMLWriter.render_span(_(" (%s left)") % value, style="color: #DDD")

        return HTMLWriter.render_span(_(" (outdated)"), style="color: darkred")


class NodeRenderer(ABCNodeRenderer):
    def _show_row_value(
        self,
        value: Any,
        col_hint: ColumnDisplayHint,
        retention_intervals: Optional[RetentionIntervals] = None,
    ) -> None:
        self._show_child_value(value, col_hint, retention_intervals)

    def show_attribute(
        self,
        value: Any,
        attr_hint: AttributeDisplayHint,
        retention_intervals: Optional[RetentionIntervals] = None,
    ) -> None:
        self._show_child_value(value, attr_hint, retention_intervals)


class DeltaNodeRenderer(ABCNodeRenderer):
    def _show_row_value(
        self,
        value: Any,
        col_hint: ColumnDisplayHint,
        retention_intervals: Optional[RetentionIntervals] = None,
    ) -> None:
        self._show_delta_child_value(value, col_hint)

    def show_attribute(
        self,
        value: Any,
        attr_hint: AttributeDisplayHint,
        retention_intervals: Optional[RetentionIntervals] = None,
    ) -> None:
        self._show_delta_child_value(value, attr_hint)

    def _show_delta_child_value(
        self,
        value: Any,
        hint: Union[ColumnDisplayHint, AttributeDisplayHint],
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
