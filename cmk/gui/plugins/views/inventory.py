#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import abc
from typing import Dict, List, Tuple, Union, Callable, Any, Sequence, Mapping
from functools import partial

from six import ensure_str

from livestatus import SiteId

from cmk.utils.regex import regex
import cmk.utils.defines as defines
import cmk.utils.render
from cmk.utils.structured_data import StructuredDataTree
from cmk.utils.type_defs import HostName

import cmk.gui.pages
import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.inventory as inventory
from cmk.gui.i18n import _
from cmk.gui.globals import g, html, request
from cmk.gui.htmllib import HTML
from cmk.gui.valuespec import Dictionary, Checkbox
from cmk.gui.escaping import escape_text
from cmk.gui.plugins.visuals import (
    filter_registry,
    VisualInfo,
    visual_info_registry,
)

from cmk.gui.plugins.visuals.inventory import (
    FilterInvText,
    FilterInvBool,
    FilterInvFloat,
    FilterInvtableText,
    FilterInvtableIDRange,
)

from cmk.gui.plugins.views import (
    data_source_registry,
    ABCDataSource,
    RowTable,
    painter_registry,
    Painter,
    register_painter,
    register_sorter,
    display_options,
    painter_option_registry,
    PainterOption,
    PainterOptions,
    inventory_displayhints,
    multisite_builtin_views,
    paint_age,
    declare_1to1_sorter,
    cmp_simple_number,
    render_labels,
)

from cmk.gui.utils.urls import makeuri_contextless

PaintResult = Tuple[str, Union[str, HTML]]

_PAINT_FUNCTION_NAME_PREFIX = "inv_paint_"
_PAINT_FUNCTIONS = {}


def update_paint_functions(mapping):
    # Update paint functions from
    # 1. views (local web plugins are loaded including display hints and paint functions)
    # 2. here
    _PAINT_FUNCTIONS.update(
        {k: v for k, v in mapping.items() if k.startswith(_PAINT_FUNCTION_NAME_PREFIX)})


def _get_paint_function_from_globals(paint_name):
    # Do not overwrite local paint functions
    update_paint_functions({k: v for k, v in globals().items() if k not in _PAINT_FUNCTIONS})
    return _PAINT_FUNCTIONS[_PAINT_FUNCTION_NAME_PREFIX + paint_name]


def paint_host_inventory_tree(row, invpath=".", column="host_inventory"):
    hostname = row.get("host_name")
    if len(sites_with_same_named_hosts := _get_sites_with_same_named_hosts(HostName(hostname))) > 1:
        html.show_error(
            _("Cannot display inventory tree of host '%s': Found this host on multiple sites: %s") %
            (hostname, ", ".join(sites_with_same_named_hosts)))
        return "", ""

    struct_tree = row.get(column)
    if struct_tree is None:
        return "", ""

    if column == "host_inventory":
        painter_options = PainterOptions.get_instance()
        tree_renderer: NodeRenderer = AttributeRenderer(
            row["site"],
            row["host_name"],
            "",
            invpath,
            show_internal_tree_paths=painter_options.get('show_internal_tree_paths'))
    else:
        tree_id = "/" + str(row["invhist_time"])
        tree_renderer = DeltaNodeRenderer(row["site"], row["host_name"], tree_id, invpath)

    parsed_path, attribute_keys = inventory.parse_tree_path(invpath)
    if attribute_keys is None:
        return _paint_host_inventory_tree_children(struct_tree, parsed_path, tree_renderer)
    return _paint_host_inventory_tree_value(struct_tree, parsed_path, tree_renderer, invpath,
                                            attribute_keys)


def _get_sites_with_same_named_hosts(hostname: HostName) -> Sequence[SiteId]:
    return _get_sites_with_same_named_hosts_cache().get(hostname, [])


def _get_sites_with_same_named_hosts_cache() -> Mapping[HostName, Sequence[SiteId]]:
    if "sites_with_same_named_hosts" in g:
        return g.sites_with_same_named_hosts

    cache = g.setdefault("sites_with_same_named_hosts", {})
    query_str = "GET hosts\nColumns: host_name\n"
    with sites.prepend_site():
        for row in sites.live().query(query_str):
            cache.setdefault(HostName(row[1]), []).append(SiteId(row[0]))
    return cache


def _paint_host_inventory_tree_children(struct_tree, parsed_path, tree_renderer):
    if parsed_path:
        children = struct_tree.get_sub_children(parsed_path)
    else:
        children = [struct_tree.get_root_container()]
    if children is None:
        return "", ""
    with html.plugged():
        for child in children:
            child.show(tree_renderer)
        code = html.drain()
    return "invtree", code


def _paint_host_inventory_tree_value(struct_tree, parsed_path, tree_renderer, invpath,
                                     attribute_keys):
    if attribute_keys == []:
        child = struct_tree.get_sub_numeration(parsed_path)
    else:
        child = struct_tree.get_sub_attributes(parsed_path)

    if child is None:
        return "", ""

    with html.plugged():
        if invpath.endswith(".") or invpath.endswith(":"):
            invpath = invpath[:-1]
        if attribute_keys == []:
            tree_renderer.show_numeration(child, path=invpath)
        elif attribute_keys:
            # In paint_host_inventory_tree we parse invpath and get
            # a path and attribute_keys which may be either None, [], or ["KEY"].
            tree_renderer.show_attribute(child.get_child_data().get(attribute_keys[-1]),
                                         _inv_display_hint(invpath))
        code = html.drain()
    return "", code


def _inv_filter_info():
    return {
        "bytes": {
            "unit": _("MB"),
            "scale": 1024 * 1024
        },
        "bytes_rounded": {
            "unit": _("MB"),
            "scale": 1024 * 1024
        },
        "hz": {
            "unit": _("MHz"),
            "scale": 1000000
        },
        "volt": {
            "unit": _("Volt")
        },
        "timestamp": {
            "unit": _("secs")
        },
    }


# Declares painters, sorters and filters to be used in views based on all host related datasources.
def _declare_inv_column(invpath, datatype, title, short=None, is_show_more: bool = True):
    if invpath == ".":
        name = "inv"
    else:
        name = "inv_" + invpath.replace(":", "_").replace(".", "_").strip("_")

    is_leaf_node = invpath[-1] not in ":."

    # Declare column painter
    painter_spec = {
        "title": invpath == "." and _("Inventory Tree") or (_("Inventory") + ": " + title),
        "columns": ["host_inventory", "host_structured_status"],
        "options": ["show_internal_tree_paths"],
        "params": Dictionary(title=_("Report options"),
                             elements=[
                                 ("use_short",
                                  Checkbox(
                                      title=_("Use short title in reports header"),
                                      default_value=False,
                                  )),
                             ],
                             required_keys=['use_short']),
        # Only leaf nodes can be shown in reports. There is currently no way to render trees.
        # The HTML code would simply be stripped by the default rendering mechanism which does
        # not look good for the HW/SW inventory tree
        "printable": is_leaf_node,
        "load_inv": True,
        "paint": lambda row: paint_host_inventory_tree(row, invpath),
        "sorter": name,
    }
    if short:
        painter_spec["short"] = short
    register_painter(name, painter_spec)

    # Sorters and Filters only for leaf nodes
    if is_leaf_node:
        # Declare sorter. It will detect numbers automatically
        register_sorter(
            name, {
                "_inv_path": invpath,
                "title": _("Inventory") + ": " + title,
                "columns": ["host_inventory", "host_structured_status"],
                "load_inv": True,
                "cmp": lambda self, a, b: _cmp_inventory_node(a, b, self._spec["_inv_path"]),
            })

        filter_info = _inv_filter_info().get(datatype, {})

        # Declare filter. Sync this with _declare_invtable_column()
        if datatype == "str":
            filter_registry.register(
                FilterInvText(
                    ident=name,
                    title=title,
                    inv_path=invpath,
                    is_show_more=is_show_more,
                ))
        elif datatype == "bool":
            filter_registry.register(
                FilterInvBool(
                    ident=name,
                    title=title,
                    inv_path=invpath,
                    is_show_more=is_show_more,
                ))
        else:
            filter_registry.register(
                FilterInvFloat(
                    ident=name,
                    title=title,
                    inv_path=invpath,
                    unit=filter_info.get("unit"),
                    scale=filter_info.get("scale", 1.0),
                    is_show_more=is_show_more,
                ))


def _cmp_inventory_node(a: Dict[str, StructuredDataTree], b: Dict[str, StructuredDataTree],
                        invpath: str) -> int:
    # TODO merge with _decorate_sort_func
    # Returns
    # (1)  1 if val_a > val_b
    # (2)  0 if val_a == val_b
    # (3) -1 if val_a < val_b
    val_a = inventory.get_inventory_data(a["host_inventory"], invpath)
    val_b = inventory.get_inventory_data(b["host_inventory"], invpath)

    if val_a is None:
        # as (2) or (3)
        return 0 if val_b is None else -1

    if val_b is None:
        # as (2) or (1)
        return 0 if val_a is None else 1

    return (val_a > val_b) - (val_a < val_b)


@painter_option_registry.register
class PainterOptionShowInternalTreePaths(PainterOption):
    @property
    def ident(self):
        return "show_internal_tree_paths"

    @property
    def valuespec(self):
        return Checkbox(
            title=_("Show internal tree paths"),
            default_value=False,
        )


@painter_registry.register
class PainterInventoryTree(Painter):
    @property
    def ident(self):
        return "inventory_tree"

    def title(self, cell):
        return _("Hardware & Software Tree")

    @property
    def columns(self):
        return ['host_inventory', 'host_structured_status']

    @property
    def painter_options(self):
        return ['show_internal_tree_paths']

    @property
    def load_inv(self):
        return True

    def render(self, row, cell):
        return paint_host_inventory_tree(row)


class ABCRowTable(RowTable):
    def __init__(self, info_names, add_host_columns):
        super(ABCRowTable, self).__init__()
        self._info_names = info_names
        self._add_host_columns = add_host_columns

    def query(self, view, columns, headers, only_sites, limit, all_active_filters):
        self._add_declaration_errors()

        # Create livestatus filter for filtering out hosts
        host_columns = ["host_name"] + list({
            c for c in columns if c.startswith("host_") and c != "host_name"
        }) + self._add_host_columns

        query = "GET hosts\n"
        query += "Columns: " + (" ".join(host_columns)) + "\n"
        query += "".join(
            filt.filter(info_name) for filt in all_active_filters for info_name in self._info_names)

        if config.debug_livestatus_queries and html.output_format == "html" and display_options.enabled(
                display_options.W):
            html.open_div(class_="livestatus message", onmouseover="this.style.display=\'none\';")
            html.open_tt()
            html.write(query.replace('\n', '<br>\n'))
            html.close_tt()
            html.close_div()

        data = self._get_raw_data(only_sites, query)

        # Now create big table of all inventory entries of these hosts
        headers = ["site"] + host_columns
        rows = []
        for row in data:
            hostrow = dict(zip(headers, row))
            for subrow in self._get_rows(hostrow):
                subrow.update(hostrow)
                rows.append(subrow)
        return rows, len(data)

    def _get_raw_data(self, only_sites, query):
        sites.live().set_only_sites(only_sites)
        sites.live().set_prepend_site(True)
        data = sites.live().query(query)
        sites.live().set_prepend_site(False)
        sites.live().set_only_sites(None)
        return data

    def _get_rows(self, hostrow):
        inv_data = self._get_inv_data(hostrow)
        return self._prepare_rows(inv_data)

    @abc.abstractmethod
    def _get_inv_data(self, hostrow):
        raise NotImplementedError()

    @abc.abstractmethod
    def _prepare_rows(self, inv_data):
        raise NotImplementedError()

    def _add_declaration_errors(self):
        pass


#.
#   .--paint helper--------------------------------------------------------.
#   |                   _       _     _          _                         |
#   |       _ __   __ _(_)_ __ | |_  | |__   ___| |_ __   ___ _ __         |
#   |      | '_ \ / _` | | '_ \| __| | '_ \ / _ \ | '_ \ / _ \ '__|        |
#   |      | |_) | (_| | | | | | |_  | | | |  __/ | |_) |  __/ |           |
#   |      | .__/ \__,_|_|_| |_|\__| |_| |_|\___|_| .__/ \___|_|           |
#   |      |_|                                    |_|                      |
#   '----------------------------------------------------------------------'


def decorate_inv_paint(skip_painting_if_string=False):
    def decorator(f):
        def wrapper(v):
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

    return "if_state " + css_class, \
        defines.interface_oper_state_name(oper_status, "%s" % oper_status).replace(" ", "&nbsp;")


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
    return "if_state " + (available and "if_available" or "if_not_available"), \
                         (available and _("free") or _("used"))


@decorate_inv_paint()
def inv_paint_mssql_is_clustered(clustered: bool) -> PaintResult:
    return "mssql_" + (clustered and "is_clustered" or "is_not_clustered"), \
                      (clustered and _("is clustered") or _("is not clustered"))


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
            time.mktime((
                broken.tm_year,
                broken.tm_mon,
                broken.tm_mday,
                0,
                0,
                0,
                broken.tm_wday,
                broken.tm_yday,
                broken.tm_isdst,
            )))

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
    return "labels", html.render_br().join(csv_list.split(","))


@decorate_inv_paint()
def inv_paint_cmk_label(label: List[str]) -> PaintResult:
    return "labels", render_labels({label[0]: label[1]},
                                   object_type="host",
                                   with_links=True,
                                   label_sources={label[0]: "discovered"})


@decorate_inv_paint()
def inv_paint_container_ready(ready: str) -> PaintResult:
    if ready == 'yes':
        css_class = "if_state_up"
    elif ready == 'no':
        css_class = "if_state_down"
    else:
        css_class = "if_state_other"

    return "if_state " + css_class, ready


@decorate_inv_paint()
def inv_paint_service_status(status: str) -> PaintResult:
    if status == 'running':
        css_class = "if_state_up"
    elif status == 'stopped':
        css_class = "if_state_down"
    else:
        css_class = "if_not_available"

    return "if_state " + css_class, status


#.
#   .--display hints-------------------------------------------------------.
#   |           _ _           _               _     _       _              |
#   |        __| (_)___ _ __ | | __ _ _   _  | |__ (_)_ __ | |_ ___        |
#   |       / _` | / __| '_ \| |/ _` | | | | | '_ \| | '_ \| __/ __|       |
#   |      | (_| | \__ \ |_) | | (_| | |_| | | | | | | | | | |_\__ \       |
#   |       \__,_|_|___/ .__/|_|\__,_|\__, | |_| |_|_|_| |_|\__|___/       |
#   |                  |_|            |___/                                |
#   '----------------------------------------------------------------------'


def _inv_display_hint(invpath):
    """Generic access function to display hints
    Don't use other methods to access the hints!"""
    hint_id = _find_display_hint_id(invpath)
    hint = inventory_displayhints.get(hint_id, {})
    return _convert_display_hint(hint)


def _find_display_hint_id(invpath):
    """Looks up the display hint for the given inventory path.

    It returns either the ID of the display hint matching the given invpath
    or None in case no entry was found.

    In case no exact match is possible try to match display hints that use
    some kind of *-syntax. There are two types of cases here:

      :* -> Entries in lists (* resolves to list index numbers)
      .* -> Path entries (* resolves to a path element)

    The current logic has some limitations related to the ways stars can
    be used.
    """
    invpath = invpath.rstrip(".:")

    # Convert index of lists to *-syntax
    # e.g. ".foo.bar:18.test" to ".foo.bar:*.test"
    r = regex(r"([^\.]):[0-9]+")
    invpath = r.sub("\\1:*", invpath)

    candidates = [
        invpath,
    ]

    # Produce a list of invpath candidates with a "*" going from back to front.
    #
    # This algorithm only allows one ".*" in a invpath. It finds the match with
    # the longest path prefix before the ".*".
    #
    # TODO: Implement a generic mechanism that allows as many stars as possible
    invpath_parts = invpath.split(".")
    star_index = len(invpath_parts) - 1
    while star_index >= 0:
        parts = invpath_parts[:star_index] + ["*"] + invpath_parts[star_index + 1:]
        invpath_with_star = "%s" % ".".join(parts)
        candidates.append(invpath_with_star)
        star_index -= 1

    for candidate in candidates:
        # TODO: Better cleanup trailing ":" and "." from display hints at all. They are useless
        # for finding the right entry.
        if candidate in inventory_displayhints:
            return candidate

        if candidate + "." in inventory_displayhints:
            return candidate + "."

        if candidate + ":" in inventory_displayhints:
            return candidate + ":"

    return None


def _convert_display_hint(hint):
    """Convert paint type to paint function, for the convenciance of the called"""
    if "paint" in hint:
        hint["paint_function"] = _get_paint_function_from_globals(hint["paint"])

    return hint


def _inv_titleinfo(invpath, node):
    hint = _inv_display_hint(invpath)
    icon = hint.get("icon")
    if "title" in hint:
        title = hint["title"]
        if hasattr(title, '__call__'):
            title = title(node)
    else:
        title = invpath.rstrip(".").rstrip(':').split('.')[-1].split(':')[-1].replace("_",
                                                                                      " ").title()
    return icon, title


# The titles of the last two path components of the node, e.g. "BIOS / Vendor"
def _inv_titleinfo_long(invpath, node):
    _icon, last_title = _inv_titleinfo(invpath, node)
    parent = inventory.parent_path(invpath)
    if parent:
        _icon, parent_title = _inv_titleinfo(parent, None)
        return parent_title + u" ➤ " + last_title
    return last_title


def declare_inventory_columns():
    # create painters for node with a display hint
    for invpath, hint in inventory_displayhints.items():
        if "*" not in invpath:
            datatype = hint.get("paint", "str")
            long_title = _inv_titleinfo_long(invpath, None)
            _declare_inv_column(invpath,
                                datatype,
                                long_title,
                                hint.get("short", hint["title"]),
                                is_show_more=hint.get("is_show_more", True))


#.
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


def _inv_find_subtable_columns(invpath):
    """Find the name of all columns of an embedded table that have a display
    hint. Respects the order of the columns if one is specified in the
    display hint.

    Also use the names found in keyorder to get even more of the available columns."""
    subtable_hint = inventory_displayhints[invpath]

    # Create dict from column name to its order number in the list
    with_numbers = enumerate(subtable_hint.get("keyorder", []))
    swapped = [(t[1], t[0]) for t in with_numbers]
    order = dict(swapped)

    columns = []
    for path in inventory_displayhints:
        if path.startswith(invpath + "*."):
            # ".networking.interfaces:*.port_type" -> "port_type"
            columns.append(path.split(".")[-1])

    for key in subtable_hint.get("keyorder", []):
        if key not in columns:
            columns.append(key)

    return sorted(columns, key=lambda x: (order.get(x, 999), x))


def _decorate_sort_func(f):
    def wrapper(val_a, val_b):
        if val_a is None:
            return 0 if val_b is None else -1

        if val_b is None:
            return 0 if val_a is None else 1

        return f(val_a, val_b)

    return wrapper


def _declare_invtable_column(infoname, invpath, topic, name, column):
    sub_invpath = invpath + "*." + name
    hint = inventory_displayhints.get(sub_invpath, {})

    def cmp_func(a, b):
        return (a > b) - (a < b)

    sortfunc = hint.get("sort", cmp_func)
    if "paint" in hint:
        paint_name = hint["paint"]
        paint_function = _get_paint_function_from_globals(paint_name)
    else:
        paint_name = "str"
        paint_function = inv_paint_generic

    title = _inv_titleinfo(sub_invpath, None)[1]

    # Sync this with _declare_inv_column()
    filter_class = hint.get("filter")
    if not filter_class:
        if paint_name == "str":
            filter_class = FilterInvtableText
        else:
            filter_class = FilterInvtableIDRange

    filter_registry.register(
        filter_class(
            inv_info=infoname,
            ident=infoname + "_" + name,
            title=topic + ": " + title,
        ))

    register_painter(
        column, {
            "title": topic + ": " + title,
            "short": hint.get("short", title),
            "columns": [column],
            "paint": lambda row: paint_function(row.get(column)),
            "sorter": column,
        })

    register_sorter(
        column, {
            "title": _("Inventory") + ": " + title,
            "columns": [column],
            "cmp": lambda self, a, b: _decorate_sort_func(sortfunc)(a.get(column), b.get(column)),
        })


class RowTableInventory(ABCRowTable):
    def __init__(self, info_name, inventory_path):
        super(RowTableInventory, self).__init__([info_name], ["host_structured_status"])
        self._inventory_path = inventory_path

    def _get_inv_data(self, hostrow):
        try:
            merged_tree = inventory.load_filtered_and_merged_tree(hostrow)
        except inventory.LoadStructuredDataError:
            html.add_user_error(
                "load_inventory_tree",
                _("Cannot load HW/SW inventory tree %s. Please remove the corrupted file.") %
                inventory.get_short_inventory_filepath(hostrow.get("host_name", "")))
            return []

        if merged_tree is None:
            return []

        invdata = inventory.get_inventory_data(merged_tree, self._inventory_path)
        if invdata is None:
            return []
        return invdata

    def _prepare_rows(self, inv_data):
        info_name = self._info_names[0]
        entries = []
        for entry in inv_data:
            newrow = {}
            for key, value in entry.items():
                newrow[info_name + "_" + key] = value
            entries.append(newrow)
        return entries


class ABCDataSourceInventory(ABCDataSource):
    @property
    def ignore_limit(self):
        return True

    @abc.abstractproperty
    def inventory_path(self) -> str:
        raise NotImplementedError()


# One master function that does all
def declare_invtable_view(infoname, invpath, title_singular, title_plural, icon=None):
    _register_info_class(infoname, title_singular, title_plural)

    # Create the datasource (like a database view)
    ds_class = type(
        "DataSourceInventory%s" % infoname.title(), (ABCDataSourceInventory,), {
            "_ident": infoname,
            "_inventory_path": invpath,
            "_title": "%s: %s" % (_("Inventory"), title_plural),
            "_infos": ["host", infoname],
            "ident": property(lambda s: s._ident),
            "title": property(lambda s: s._title),
            "table": property(lambda s: RowTableInventory(s._ident, s._inventory_path)),
            "infos": property(lambda s: s._infos),
            "keys": property(lambda s: []),
            "id_keys": property(lambda s: []),
            "inventory_path": property(lambda s: s._inventory_path),
        })
    data_source_registry.register(ds_class)

    painters = []
    filters = []
    for name in _inv_find_subtable_columns(invpath):
        column = infoname + "_" + name

        # Declare a painter, sorter and filters for each path with display hint
        _declare_invtable_column(infoname, invpath, title_singular, name, column)

        painters.append((column, '', ''))
        filters.append(column)

    _declare_views(infoname, title_plural, painters, filters, [invpath], icon)


class RowMultiTableInventory(ABCRowTable):
    def __init__(self, sources, match_by, errors):
        super(RowMultiTableInventory, self).__init__([infoname for infoname, _path in sources],
                                                     ["host_structured_status"])
        self._sources = sources
        self._match_by = match_by
        self._errors = errors

    def _get_inv_data(self, hostrow):
        try:
            merged_tree = inventory.load_filtered_and_merged_tree(hostrow)
        except inventory.LoadStructuredDataError:
            html.add_user_error(
                "load_inventory_tree",
                _("Cannot load HW/SW inventory tree %s. Please remove the corrupted file.") %
                inventory.get_short_inventory_filepath(hostrow.get("host_name", "")))
            return []

        if merged_tree is None:
            return []

        multi_inv_data = []
        for info_name, inventory_path in self._sources:
            inv_data = inventory.get_inventory_data(merged_tree, inventory_path)
            if inv_data is None:
                continue
            multi_inv_data.append((info_name, inv_data))
        return multi_inv_data

    def _prepare_rows(self, inv_data):
        joined_rows: Dict[Tuple[str, ...], Dict] = {}
        for this_info_name, this_inv_data in inv_data:
            for entry in this_inv_data:
                inst = joined_rows.setdefault(tuple(entry[key] for key in self._match_by), {})
                inst.update({this_info_name + "_" + k: v for k, v in entry.items()})
        return [joined_rows[match_by_key] for match_by_key in sorted(joined_rows)]

    def _add_declaration_errors(self):
        if self._errors:
            html.add_user_error("declare_invtable_view", ", ".join(self._errors))


def declare_joined_inventory_table_view(tablename, title_singular, title_plural, tables, match_by):

    _register_info_class(tablename, title_singular, title_plural)

    info_names: List[str] = []
    invpaths: List[str] = []
    titles: List[str] = []
    errors = []
    for this_tablename in tables:
        visual_info_class = visual_info_registry.get(this_tablename)
        data_source_class = data_source_registry.get(this_tablename)
        if data_source_class is None or visual_info_class is None:
            errors.append("Missing declare_invtable_view for inventory table view '%s'" %
                          this_tablename)
            continue

        assert issubclass(data_source_class, ABCDataSourceInventory)
        ds = data_source_class()
        info_names.append(ds.ident)
        invpaths.append(ds.inventory_path)
        titles.append(visual_info_class().title)

    # Create the datasource (like a database view)
    ds_class = type(
        "DataSourceInventory%s" % tablename.title(), (ABCDataSource,), {
            "_ident": tablename,
            "_sources": list(zip(info_names, invpaths)),
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
        })
    data_source_registry.register(ds_class)

    known_common_columns = set()
    painters = []
    filters = []
    for this_invpath, this_infoname, this_title in zip(invpaths, info_names, titles):
        for name in _inv_find_subtable_columns(this_invpath):
            if name in match_by:
                # Filter out duplicate common columns which are used to join tables
                if name in known_common_columns:
                    continue
                known_common_columns.add(name)

            column = this_infoname + "_" + name

            # Declare a painter, sorter and filters for each path with display hint
            _declare_invtable_column(this_infoname, this_invpath, this_title, name, column)

            painters.append((column, '', ''))
            filters.append(column)

    _declare_views(tablename, title_plural, painters, filters, invpaths)


def _register_info_class(infoname, title_singular, title_plural):
    # Declare the "info" (like a database table)
    info_class = type(
        "VisualInfo%s" % infoname.title(), (VisualInfo,), {
            "_ident": infoname,
            "ident": property(lambda self: self._ident),
            "_title": title_singular,
            "title": property(lambda self: self._title),
            "_title_plural": title_plural,
            "title_plural": property(lambda self: self._title_plural),
            "single_spec": property(lambda self: None),
        })
    visual_info_registry.register(info_class)


def _declare_views(infoname, title_plural, painters, filters, invpaths, icon=None):
    is_show_more = True
    if len(invpaths) == 1:
        hint = _inv_display_hint(invpaths[0])
        is_show_more = hint.get("is_show_more", True)

    # Declare two views: one for searching globally. And one
    # for the items of one host.
    view_spec = {
        'datasource': infoname,
        "topic": "inventory",
        "sort_index": 30,
        'public': True,
        'layout': 'table',
        'num_columns': 1,
        'browser_reload': 0,
        'column_headers': 'pergroup',
        'user_sortable': True,
        'play_sounds': False,
        'force_checkboxes': False,
        'mobile': False,
        'group_painters': [],
        'sorters': [],
        'is_show_more': is_show_more,
    }

    # View for searching for items
    multisite_builtin_views[infoname + "_search"] = {
        # General options
        'title': _("Search %s") % title_plural,
        'description': _('A view for searching in the inventory data for %s') % title_plural,
        'hidden': False,
        'mustsearch': True,

        # Columns
        'painters': [('host', 'inv_host', '')] + painters,

        # Filters
        'show_filters': [
            'siteopt',
            'hostregex',
            'hostgroups',
            'opthostgroup',
            'opthost_contactgroup',
            'host_address',
            'host_tags',
            'hostalias',
            'host_favorites',
        ] + filters,
        'hide_filters': [],
        'hard_filters': [],
        'hard_filtervars': [],
    }
    multisite_builtin_views[infoname + "_search"].update(view_spec)

    # View for the items of one host
    multisite_builtin_views[infoname + "_of_host"] = {
        # General options
        'title': title_plural,
        'description': _('A view for the %s of one host') % title_plural,
        'hidden': True,
        'mustsearch': False,
        'link_from': {
            'single_infos': ['host'],
            'has_inventory_tree': invpaths,
        },

        # Columns
        'painters': painters,

        # Filters
        'show_filters': filters,
        'hard_filters': [],
        'hard_filtervars': [],
        'hide_filters': ["host"],
        "icon": icon,
    }
    multisite_builtin_views[infoname + "_of_host"].update(view_spec)


# Now declare Multisite views for a couple of embedded tables
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
declare_invtable_view("invibmmqmanagers", ".software.applications.ibm_mq.managers:", _("Manager"),
                      _("IBM MQ Managers"))
declare_invtable_view("invibmmqchannels", ".software.applications.ibm_mq.channels:", _("Channel"),
                      _("IBM MQ Channels"))
declare_invtable_view("invibmmqqueues", ".software.applications.ibm_mq.queues:", _("Queue"),
                      _("IBM MQ Queues"))
declare_invtable_view("invtunnels", ".networking.tunnels:", _("Networking Tunnels"),
                      _("Networking Tunnels"))
declare_invtable_view(
    "invkernelconfig",
    ".software.kernel_config:",
    _("Kernel configuration (sysctl)"),
    _("Kernel configurations (sysctl)"),
)

# This would also be possible. But we muss a couple of display and filter hints.
# declare_invtable_view("invdisks",       ".hardware.storage.disks:",  _("Hard Disk"),          _("Hard Disks"))

#.
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
    'datasource': 'hosts',
    'topic': 'inventory',
    'title': _('Inventory of host'),
    'description': _('The complete hardware- and software inventory of a host'),
    'icon': 'inventory',
    'hidebutton': False,
    'public': True,
    'hidden': True,
    'link_from': {
        'single_infos': ['host'],
        'has_inventory_tree': '.',
    },

    # Layout options
    'layout': 'dataset',
    'num_columns': 1,
    'browser_reload': 0,
    'column_headers': 'pergroup',
    'user_sortable': False,
    'play_sounds': False,
    'force_checkboxes': False,
    'mustsearch': False,
    'mobile': False,

    # Columns
    'group_painters': [],
    'painters': [
        ('host', 'host', ''),
        ('inv', None, ''),
    ],

    # Filters
    'hard_filters': [],
    'hard_filtervars': [],
    # Previously (<2.0/1.6??) the hide_filters: ['host, 'site'] were needed to build the URL.
    # Now for creating the URL these filters are obsolete;
    # Side effect: with 'site' in hide_filters the only_sites filter for livestatus is NOT set
    # properly. Thus we removed 'site'.
    'hide_filters': ['host'],
    'show_filters': [],
    'sorters': [],
}

generic_host_filters = multisite_builtin_views["allhosts"]["show_filters"]

# View with table of all hosts, with some basic information
multisite_builtin_views["inv_hosts_cpu"] = {
    # General options
    'datasource': 'hosts',
    "topic": "inventory",
    "sort_index": 10,
    'title': _('CPU inventory of all hosts'),
    'description': _('A list of all hosts with some CPU related inventory data'),
    'public': True,
    'hidden': False,
    'is_show_more': True,

    # Layout options
    'layout': 'table',
    'num_columns': 1,
    'browser_reload': 0,
    'column_headers': 'pergroup',
    'user_sortable': True,
    'play_sounds': False,
    'force_checkboxes': False,
    'mustsearch': False,
    'mobile': False,

    # Columns
    'group_painters': [],
    'painters': [
        ('host', 'inv_host', ''),
        ('inv_software_os_name', None, ''),
        ('inv_hardware_cpu_cpus', None, ''),
        ('inv_hardware_cpu_cores', None, ''),
        ('inv_hardware_cpu_max_speed', None, ''),
        ('perfometer', None, '', 'CPU load'),
        ('perfometer', None, '', 'CPU utilization'),
    ],

    # Filters
    'hard_filters': ['has_inv'],
    'hard_filtervars': [('is_has_inv', '1')],
    'hide_filters': [],
    'show_filters': [
        'inv_hardware_cpu_cpus',
        'inv_hardware_cpu_cores',
        'inv_hardware_cpu_max_speed',
    ],
    'sorters': [],
}

# View with available and used ethernet ports
multisite_builtin_views["inv_hosts_ports"] = {
    # General options
    'datasource': 'hosts',
    "topic": "inventory",
    "sort_index": 20,
    'title': _('Switch port statistics'),
    'description':
        _('A list of all hosts with statistics about total, used and free networking interfaces'),
    'public': True,
    'hidden': False,
    'is_show_more': False,

    # Layout options
    'layout': 'table',
    'num_columns': 1,
    'browser_reload': 0,
    'column_headers': 'pergroup',
    'user_sortable': True,
    'play_sounds': False,
    'force_checkboxes': False,
    'mustsearch': False,
    'mobile': False,

    # Columns
    'group_painters': [],
    'painters': [
        ('host', 'invinterface_of_host', ''),
        ('inv_hardware_system_product', None, ''),
        ('inv_networking_total_interfaces', None, ''),
        ('inv_networking_total_ethernet_ports', None, ''),
        ('inv_networking_available_ethernet_ports', None, ''),
    ],

    # Filters
    'hard_filters': ['has_inv'],
    'hard_filtervars': [('is_has_inv', '1')],
    'hide_filters': [],
    'show_filters': generic_host_filters + [],
    'sorters': [('inv_networking_available_ethernet_ports', True)],
}

#.
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
    def __init__(self):
        super(RowTableInventoryHistory, self).__init__(["invhist"], [])
        self._inventory_path = None

    def _get_inv_data(self, hostrow):
        hostname = hostrow.get("host_name")
        history_deltas, corrupted_history_files = inventory.get_history_deltas(hostname)
        if corrupted_history_files:
            html.add_user_error(
                "load_inventory_delta_tree",
                _("Cannot load HW/SW inventory history entries %s. Please remove the corrupted files."
                  % ", ".join(sorted(corrupted_history_files))))
        return history_deltas

    def _prepare_rows(self, inv_data):
        for timestamp, delta_info in inv_data:
            new, changed, removed, delta_tree = delta_info
            newrow = {
                "invhist_time": int(timestamp),
                "invhist_delta": delta_tree,
                "invhist_removed": removed,
                "invhist_new": new,
                "invhist_changed": changed,
            }
            yield newrow


@data_source_registry.register
class DataSourceInventoryHistory(ABCDataSource):
    @property
    def ident(self):
        return "invhist"

    @property
    def title(self):
        return _("Inventory: History")

    @property
    def table(self):
        return RowTableInventoryHistory()

    @property
    def infos(self):
        return ["host", "invhist"]

    @property
    def keys(self):
        return []

    @property
    def id_keys(self):
        return ["host_name", "invhist_time"]


@painter_registry.register
class PainterInvhistTime(Painter):
    @property
    def ident(self):
        return "invhist_time"

    def title(self, cell):
        return _("Inventory Date/Time")

    def short_title(self, cell):
        return _("Date/Time")

    @property
    def columns(self):
        return ['invhist_time']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["invhist_time"], True, 60 * 10)


@painter_registry.register
class PainterInvhistDelta(Painter):
    @property
    def ident(self):
        return "invhist_delta"

    def title(self, cell):
        return _("Inventory changes")

    @property
    def columns(self):
        return ["invhist_delta", "invhist_time"]

    def render(self, row, cell):
        return paint_host_inventory_tree(row, column="invhist_delta")


def paint_invhist_count(row, what):
    number = row["invhist_" + what]
    if number:
        return "narrow number", str(number)
    return "narrow number unused", "0"


@painter_registry.register
class PainterInvhistRemoved(Painter):
    @property
    def ident(self):
        return "invhist_removed"

    def title(self, cell):
        return _("Removed entries")

    def short_title(self, cell):
        return _("Removed")

    @property
    def columns(self):
        return ['invhist_removed']

    def render(self, row, cell):
        return paint_invhist_count(row, "removed")


@painter_registry.register
class PainterInvhistNew(Painter):
    @property
    def ident(self):
        return "invhist_new"

    def title(self, cell):
        return _("new entries")

    def short_title(self, cell):
        return _("new")

    @property
    def columns(self):
        return ['invhist_new']

    def render(self, row, cell):
        return paint_invhist_count(row, "new")


@painter_registry.register
class PainterInvhistChanged(Painter):
    @property
    def ident(self):
        return "invhist_changed"

    def title(self, cell):
        return _("changed entries")

    def short_title(self, cell):
        return _("changed")

    @property
    def columns(self):
        return ['invhist_changed']

    def render(self, row, cell):
        return paint_invhist_count(row, "changed")


# sorters
declare_1to1_sorter("invhist_time", cmp_simple_number, reverse=True)
declare_1to1_sorter("invhist_removed", cmp_simple_number)
declare_1to1_sorter("invhist_new", cmp_simple_number)
declare_1to1_sorter("invhist_changed", cmp_simple_number)

# View for inventory history of one host

multisite_builtin_views["inv_host_history"] = {
    # General options
    'datasource': 'invhist',
    'topic': 'inventory',
    'title': _('Inventory history of host'),
    'description': _('The history for changes in hardware- and software inventory of a host'),
    'icon': {
        'icon': 'inventory',
        'emblem': 'time',
    },
    'hidebutton': False,
    'public': True,
    'hidden': True,
    'is_show_more': True,
    'link_from': {
        'single_infos': ['host'],
        'has_inventory_tree_history': '.',
    },

    # Layout options
    'layout': 'table',
    'num_columns': 1,
    'browser_reload': 0,
    'column_headers': 'pergroup',
    'user_sortable': True,
    'play_sounds': False,
    'force_checkboxes': False,
    'mustsearch': False,
    'mobile': False,

    # Columns
    'group_painters': [],
    'painters': [
        ('invhist_time', None, ''),
        ('invhist_removed', None, ''),
        ('invhist_new', None, ''),
        ('invhist_changed', None, ''),
        ('invhist_delta', None, ''),
    ],

    # Filters
    'hard_filters': [],
    'hard_filtervars': [],
    'hide_filters': ['host'],
    'show_filters': [],
    'sorters': [('invhist_time', False)],
}

#.
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


def _sort_by_index(keyorder, item):
    try:
        return keyorder.index(item[0])
    except ValueError:
        return len(keyorder) + 1


class NodeRenderer:
    def __init__(self, site_id, hostname, tree_id, invpath, show_internal_tree_paths=False):
        self._site_id = site_id
        self._hostname = hostname
        self._tree_id = tree_id
        self._invpath = invpath
        if show_internal_tree_paths:
            self._show_internal_tree_paths = "on"
        else:
            self._show_internal_tree_paths = ""

    #   ---container------------------------------------------------------------

    def show_container(self, container, path=None):
        for _x, node in container.get_edge_nodes():
            node_abs_path = node.get_absolute_path()

            raw_invpath = self._get_raw_path(".".join(map(str, node_abs_path)))
            invpath = ".%s." % raw_invpath

            icon, title = _inv_titleinfo(invpath, node)

            # Replace placeholders in title with the real values for this path
            if "%d" in title or "%s" in title:
                title = self._replace_placeholders(title, invpath)

            header = self._get_header(title, ".".join(map(str, node_abs_path)), "#666")
            fetch_url = makeuri_contextless(
                request,
                [
                    ("site", self._site_id),
                    ("host", self._hostname),
                    ("path", invpath),
                    ("show_internal_tree_paths", self._show_internal_tree_paths),
                    ("treeid", self._tree_id),
                ],
                "ajax_inv_render_tree.py",
            )

            if html.begin_foldable_container("inv_%s%s" % (self._hostname, self._tree_id),
                                             invpath,
                                             False,
                                             header,
                                             icon=icon,
                                             fetch_url=fetch_url):
                # Render only if it is open. We'll get the stuff via ajax later if it's closed
                for child in inventory.sort_children(node.get_node_children()):
                    child.show(self, path=raw_invpath)
            html.end_foldable_container()

    def _replace_placeholders(self, raw_title, invpath):
        hint_id = _find_display_hint_id(invpath)
        invpath_parts = invpath.strip(".").split(".")

        # Use the position of the stars in the path to build a list of texts
        # that should be used for replacing the tile placeholders
        replace_vars = []
        hint_parts = hint_id.strip(".").split(".")
        for index, hint_part in enumerate(hint_parts):
            if hint_part == "*":
                replace_vars.append(invpath_parts[index])

        # Now replace the variables in the title. Handle the case where we have
        # more stars than macros in the title.
        num_macros = raw_title.count("%d") + raw_title.count("%s")
        return raw_title % tuple(replace_vars[:num_macros])

    #   ---numeration-----------------------------------------------------------

    def show_numeration(self, numeration, path=None):
        #FIXME these kind of paths are required for hints.
        # Clean this up one day.
        invpath = ".%s:" % self._get_raw_path(path)
        hint = _inv_display_hint(invpath)
        keyorder = hint.get("keyorder", [])  # well known keys
        data = numeration.get_child_data()

        # Add titles for those keys
        titles = []
        for key in keyorder:
            sub_invpath = "%s0.%s" % (invpath, key)
            _icon, title = _inv_titleinfo(sub_invpath, None)
            sub_hint = _inv_display_hint(sub_invpath)
            short_title = sub_hint.get("short", title)
            titles.append((short_title, key))

        # Determine *all* keys, in order to find unknown ones
        keys = self._get_numeration_keys(data)

        # Order not well-known keys alphabetically
        extratitles = []
        for key in keys:
            if key not in keyorder:
                _icon, title = _inv_titleinfo("%s0.%s" % (invpath, key), None)
                extratitles.append((title, key))
        titles += sorted(extratitles)

        # Link to Multisite view with exactly this table
        if "view" in hint:
            url = makeuri_contextless(
                request,
                [
                    ("view_name", hint["view"]),
                    ("host", self._hostname),
                ],
                filename="view.py",
            )
            html.div(html.render_a(_("Open this table for filtering / sorting"), href=url),
                     class_="invtablelink")

        self._show_numeration_table(titles, invpath, data)

    def _get_numeration_keys(self, data):
        keys = set([])
        for entry in data:
            keys.update(entry.keys())
        return keys

    def _show_numeration_table(self, titles, invpath, data):
        # TODO: Use table.open_table() below.
        html.open_table(class_="data")
        html.open_tr()
        for title, key in titles:
            html.th(self._get_header(title, key, "#DDD"))
        html.close_tr()
        for index, entry in enumerate(data):
            html.open_tr(class_="even0")
            for title, key in titles:
                value = entry.get(key)
                sub_invpath = "%s%d.%s" % (invpath, index, key)
                hint = _inv_display_hint(sub_invpath)
                if "paint_function" in hint:
                    #FIXME At the moment  we need it to get tdclass
                    # Clean this up one day.
                    # The value is not really needed, but we need to deal with the delta mode
                    unused_value = value[1] if isinstance(value, tuple) else value
                    tdclass, _ = hint["paint_function"](unused_value)
                else:
                    tdclass = None

                html.open_td(class_=tdclass)
                self._show_numeration_value(value, hint)
                html.close_td()
            html.close_tr()
        html.close_table()

    def _show_numeration_value(self, value, hint):
        raise NotImplementedError()

    #   ---attributes-----------------------------------------------------------

    def show_attributes(self, attributes, path=None):
        invpath = ".%s" % self._get_raw_path(path)
        hint = _inv_display_hint(invpath)

        keyorder = hint.get("keyorder")
        if keyorder:
            sort_func: Union[partial[Tuple[str, Any]],
                             Callable[[Tuple[str, Any]], str]] = partial(_sort_by_index, keyorder)
        else:
            # Simply sort by keys
            def sort_func(item):
                return item[0]

        html.open_table()
        for key, value in sorted(attributes.get_child_data().items(), key=sort_func):
            sub_invpath = "%s.%s" % (invpath, key)
            _icon, title = _inv_titleinfo(sub_invpath, key)
            hint = _inv_display_hint(sub_invpath)

            html.open_tr()
            html.open_th(title=sub_invpath)
            html.write(self._get_header(title, key, "#DDD"))
            html.close_th()
            html.open_td()
            self.show_attribute(value, hint)
            html.close_td()
            html.close_tr()
        html.close_table()

    def show_attribute(self, value, hint):
        raise NotImplementedError()

    #   ---helper---------------------------------------------------------------

    def _get_raw_path(self, path):
        if path is None:
            return self._invpath.strip(".")
        return path.strip(".")

    def _get_header(self, title, key, hex_color):
        header = HTML(title)
        if self._show_internal_tree_paths:
            header += HTML(" <span style='color: %s'>(%s)</span>" % (hex_color, key))
        return header

    def _show_child_value(self, value, hint):
        if "paint_function" in hint:
            _tdclass, code = hint["paint_function"](value)
            html.write(code)
        elif isinstance(value, str):
            html.write_text(ensure_str(value))
        elif isinstance(value, int):
            html.write(str(value))
        elif isinstance(value, float):
            html.write("%.2f" % value)
        elif value is not None:
            html.write(str(value))


class AttributeRenderer(NodeRenderer):
    def _show_numeration_value(self, value, hint):
        self._show_child_value(value, hint)

    def show_attribute(self, value, hint):
        self._show_child_value(value, hint)


class DeltaNodeRenderer(NodeRenderer):
    def _show_numeration_value(self, value, hint):
        if value is None:
            value = (None, None)
        self.show_attribute(value, hint)

    def show_attribute(self, value, hint):
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
            html.write(u" → ")
            html.open_span(class_="invnew")
            self._show_child_value(new, hint)
            html.close_span()


# Ajax call for fetching parts of the tree
@cmk.gui.pages.register("ajax_inv_render_tree")
def ajax_inv_render_tree():
    site_id = html.request.var("site")
    hostname = request.get_ascii_input_mandatory("host")
    inventory.verify_permission(hostname, site_id)

    invpath = html.request.var("path")
    tree_id = html.request.var("treeid", "")
    show_internal_tree_paths = bool(html.request.var("show_internal_tree_paths"))

    if tree_id:
        struct_tree, corrupted_history_files = \
            inventory.load_delta_tree(hostname, int(tree_id[1:]))
        if corrupted_history_files:
            html.add_user_error(
                "load_inventory_delta_tree",
                _("Cannot load HW/SW inventory history entries %s. Please remove the corrupted files."
                 ) % ", ".join(corrupted_history_files))
            return
        tree_renderer: NodeRenderer = DeltaNodeRenderer(site_id, hostname, tree_id, invpath)

    else:
        row = inventory.get_status_data_via_livestatus(site_id, hostname)
        try:
            struct_tree = inventory.load_filtered_and_merged_tree(row)
        except inventory.LoadStructuredDataError:
            html.add_user_error(
                "load_inventory_tree",
                _("Cannot load HW/SW inventory tree %s. Please remove the corrupted file.") %
                inventory.get_short_inventory_filepath(hostname))
            return
        tree_renderer = AttributeRenderer(site_id,
                                          hostname,
                                          "",
                                          invpath,
                                          show_internal_tree_paths=show_internal_tree_paths)

    if struct_tree is None:
        html.show_error(_("No such inventory tree."))
        return

    parsed_path, _attribute_keys = inventory.parse_tree_path(invpath)
    if parsed_path:
        children = struct_tree.get_sub_children(parsed_path)
    else:
        children = [struct_tree.get_root_container()]

    if children is None:
        html.show_error(
            _("Invalid path in inventory tree: '%s' >> %s") % (invpath, repr(parsed_path)))
    else:
        for child in inventory.sort_children(children):
            child.show(tree_renderer, path=invpath)
