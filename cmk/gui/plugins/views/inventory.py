#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.regex import regex
import cmk.defines as defines
import cmk.render

import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.utils as utils
import cmk.gui.inventory as inventory
from cmk.gui.i18n import _
from cmk.gui.valuespec import *

import cmk.gui.plugins.visuals
import cmk.gui.plugins.visuals.inventory
from cmk.gui.plugins.visuals.inventory import (
    FilterInvText,
    FilterInvBool,
    FilterInvFloat,
    FilterInvtableVersion,
    FilterInvtableIDRange,
    FilterInvtableOperStatus,
    FilterInvtableAdminStatus,
    FilterInvtableAvailable,
    FilterInvtableInterfaceType,
    FilterInvtableTimestampAsAge,
    FilterInvtableText,
    FilterInvtableIDRange,
)

from . import (
    painter_options,
    display_options,
    multisite_painters,
    multisite_sorters,
    multisite_painter_options,
    inventory_displayhints,
    multisite_datasources,
    multisite_builtin_views,
    view_is_enabled,
    paint_age,
    declare_1to1_sorter,
    cmp_simple_number,
)

def paint_host_inventory_tree(row, invpath=".", column="host_inventory"):
    struct_tree = row.get(column)
    if struct_tree is None:
        return "", ""

    if column == "host_inventory":
        tree_renderer = AttributeRenderer(row["host_name"], "", invpath,
                        show_internal_tree_paths=painter_options.get('show_internal_tree_paths'))
    else:
        tree_id = "/" + str(row["invhist_time"])
        tree_renderer = DeltaNodeRenderer(row["host_name"], tree_id, invpath)

    parsed_path, attributes_key = inventory.parse_tree_path(invpath)
    if attributes_key is None:
        return _paint_host_inventory_tree_children(struct_tree, parsed_path, tree_renderer)
    else:
        return _paint_host_inventory_tree_value(struct_tree, parsed_path, tree_renderer, invpath, attributes_key)


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


def _paint_host_inventory_tree_value(struct_tree, parsed_path, tree_renderer, invpath, attributes_key):
    if attributes_key == []:
        child = struct_tree.get_sub_numeration(parsed_path)
    else:
        child = struct_tree.get_sub_attributes(parsed_path)

    if child is None:
        return  "", ""

    with html.plugged():
        if invpath.endswith(".") or invpath.endswith(":"):
            invpath = invpath[:-1]
        if attributes_key == []:
            tree_renderer.show_numeration(child, path=invpath)
        else:
            tree_renderer.show_attribute(child.get_child_data().get(attributes_key),
                                         _inv_display_hint(invpath))
        code = html.drain()
    return "", code


inv_filter_info = {
    "bytes"         : { "unit" : _("MB"),    "scale" : 1024*1024 },
    "bytes_rounded" : { "unit" : _("MB"),    "scale" : 1024*1024 },
    "hz"            : { "unit" : _("MHz"),   "scale" : 1000000 },
    "volt"          : { "unit" : _("Volt") },
    "timestamp"     : { "unit" : _("secs") },
}


# Declares painters, sorters and filters to be used in views based on all host related datasources.
def declare_inv_column(invpath, datatype, title, short = None):
    if invpath == ".":
        name = "inv"
    else:
        name = "inv_" + invpath.replace(":", "_").replace(".", "_").strip("_")

    # Declare column painter
    multisite_painters[name] = {
        "title"    : invpath == "." and _("Inventory Tree") or (_("Inventory") + ": " + title),
        "columns"  : ["host_inventory"],
        "options"  : ["show_internal_tree_paths"],
        "load_inv" : True,
        "paint"    : lambda row: paint_host_inventory_tree(row, invpath),
        "sorter"   : name,
    }
    if short:
        multisite_painters[name]["short"] = short

    # Sorters and Filters only for leaf nodes
    if invpath[-1] not in ":.":
        # Declare sorter. It will detect numbers automatically
        multisite_sorters[name] = {
            "title"    : _("Inventory") + ": " + title,
            "columns"  : ["host_inventory"],
            "load_inv" : True,
            "cmp"      : lambda a, b: cmp_inventory_node(a, b, invpath),
        }

        # Declare filter. Sync this with declare_invtable_columns()
        if datatype == "str":
            cmk.gui.plugins.visuals.inventory.declare_filter(800, FilterInvText(name, invpath, title))
        elif datatype == "bool":
            cmk.gui.plugins.visuals.inventory.declare_filter(800, FilterInvBool(name, invpath, title))
        else:
            filter_info = inv_filter_info.get(datatype, {})
            cmk.gui.plugins.visuals.inventory.declare_filter(800, FilterInvFloat(name, invpath, title,
               unit = filter_info.get("unit"),
               scale = filter_info.get("scale", 1.0)))


def cmp_inventory_node(a, b, invpath):
    val_a = inventory.get_inventory_data(a["host_inventory"], invpath)
    val_b = inventory.get_inventory_data(b["host_inventory"], invpath)
    return cmp(val_a, val_b)


multisite_painter_options["show_internal_tree_paths"] = {
    'valuespec' : Checkbox(
        title = _("Show internal tree paths"),
        default_value = False,
    )
}


multisite_painters["inventory_tree"] = {
    "title"    : _("Hardware & Software Tree"),
    "columns"  : ["host_inventory"],
    "options"  : ["show_internal_tree_paths"],
    "load_inv" : True,
    "paint"    : paint_host_inventory_tree,
}


#.
#   .--paint helper--------------------------------------------------------.
#   |                   _       _     _          _                         |
#   |       _ __   __ _(_)_ __ | |_  | |__   ___| |_ __   ___ _ __         |
#   |      | '_ \ / _` | | '_ \| __| | '_ \ / _ \ | '_ \ / _ \ '__|        |
#   |      | |_) | (_| | | | | | |_  | | | |  __/ | |_) |  __/ |           |
#   |      | .__/ \__,_|_|_| |_|\__| |_| |_|\___|_| .__/ \___|_|           |
#   |      |_|                                    |_|                      |
#   '----------------------------------------------------------------------'


def decorate_inv_paint(f):
    def wrapper(v):
        if v in ["", None]:
            return "", ""
        else:
            return f(v)
    return wrapper


@decorate_inv_paint
def inv_paint_generic(v):
    if isinstance(v, float):
        return "number", "%.2f" % v
    elif isinstance(v, int):
        return "number", "%d" % v
    else:
        return "", html.escaper.escape_text("%s" % v)


@decorate_inv_paint
def inv_paint_hz(hz):
    if hz == None:
        return "", ""
    if hz < 10:
        return "number", "%.2f" % hz
    elif hz < 100:
        return "number", "%.1f" % hz
    elif hz < 1500:
        return "number", "%.0f" % hz
    elif hz < 1000000:
        return "number", "%.1f kHz" % (hz / 1000)
    elif hz < 1000000000:
        return "number", "%.1f MHz" % (hz / 1000000)
    else:
        return "number", "%.2f GHz" % (hz / 1000000000)


@decorate_inv_paint
def inv_paint_bytes(b):
    if b == 0:
        return "number", "0"

    units = [ 'B', 'kB', 'MB', 'GB', 'TB' ]
    i = 0
    while b % 1024 == 0 and i+1 < len(units):
        b = b / 1024
        i += 1
    return "number", "%d %s" % (b, units[i])


@decorate_inv_paint
def inv_paint_size(b):
    return "number", cmk.render.bytes(b)


@decorate_inv_paint
def inv_paint_number(b):
    return "number", str(b)


# Similar to paint_number, but is allowed to
# abbreviate things if numbers are very large
# (though it doesn't do so yet)
@decorate_inv_paint
def inv_paint_count(b):
    return "number", str(b)


@decorate_inv_paint
def inv_paint_bytes_rounded(b):
    if b == 0:
        return "number", "0"

    units = [ 'B', 'kB', 'MB', 'GB', 'TB' ]
    i = len(units) - 1
    fac = 1024 ** (len(units) - 1)
    while b < fac * 1.5 and i > 0:
        i -= 1
        fac = fac / 1024.0

    if i:
        return "number", "%.2f&nbsp;%s" % (b / fac, units[i])
    else:
        return "number", "%d&nbsp;%s" % (b, units[0])


def _nic_speed_human_readable(bits_per_second):
    if bits_per_second == 10000000:
        return "10 Mbit/s"
    elif bits_per_second == 100000000:
        return "100 Mbit/s"
    elif bits_per_second == 1000000000:
        return "1 Gbit/s"
    elif bits_per_second < 1500:
        return "%d bit/s" % bits_per_second
    elif bits_per_second < 1000000:
        return "%s Kbit/s" % utils.drop_dotzero(bits_per_second / 1000.0, digits=1)
    elif bits_per_second < 1000000000:
        return "%s Mbit/s" % utils.drop_dotzero(bits_per_second / 1000000.0, digits=2)
    else:
        return "%s Gbit/s" % utils.drop_dotzero(bits_per_second / 1000000000.0, digits=2)


@decorate_inv_paint
def inv_paint_nic_speed(bits_per_second):
    if bits_per_second:
        return "number", _nic_speed_human_readable(int(bits_per_second))
    else:
        return "", ""


@decorate_inv_paint
def inv_paint_if_oper_status(oper_status):
    if oper_status == 1:
        css_class = "if_state_up"
    elif oper_status == 2:
        css_class = "if_state_down"
    else:
        css_class = "if_state_other"

    return "if_state " + css_class, \
        defines.interface_oper_state_name(oper_status, "%s" % oper_status).replace(" ", "&nbsp;")


# admin status can only be 1 or 2, matches oper status :-)
@decorate_inv_paint
def inv_paint_if_admin_status(admin_status):
    return inv_paint_if_oper_status(admin_status)


@decorate_inv_paint
def inv_paint_if_port_type(port_type):
    type_name = defines.interface_port_types().get(port_type, _("unknown"))
    return "", "%d - %s" % (port_type, type_name)


@decorate_inv_paint
def inv_paint_if_available(available):
    return "if_state " + (available and "if_available" or "if_not_available"), \
                         (available and _("free") or _("used"))


@decorate_inv_paint
def inv_paint_mssql_is_clustered(clustered):
    return "mssql_" + (clustered and "is_clustered" or "is_not_clustered"), \
                      (clustered and _("is clustered") or _("is not clustered"))


@decorate_inv_paint
def inv_paint_mssql_node_names(node_names):
    return "", ", ".join(node_names)


@decorate_inv_paint
def inv_paint_ipv4_network(nw):
    if nw == "0.0.0.0/0":
        return "", _("Default")
    else:
        return "", nw


@decorate_inv_paint
def inv_paint_ip_address_type(t):
    if t == "ipv4":
        return "", _("IPv4")
    elif t == "ipv6":
        return "", _("IPv6")
    else:
        return "", t


@decorate_inv_paint
def inv_paint_route_type(rt):
    if rt == "local":
        return "", _("Local route")
    else:
        return "", _("Gateway route")


@decorate_inv_paint
def inv_paint_volt(volt):
    if volt:
        return "number", "%.1f V" % volt
    else:
        return "", ""


@decorate_inv_paint
def inv_paint_date(timestamp):
    if timestamp:
        date_painted = time.strftime("%Y-%m-%d", time.localtime(timestamp))
        return "number", "%s" % date_painted
    else:
        return "", ""


@decorate_inv_paint
def inv_paint_date_and_time(timestamp):
    if timestamp:
        date_painted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        return "number", "%s" % date_painted
    else:
        return "", ""


@decorate_inv_paint
def inv_paint_age(age):
    if age:
        return "number", cmk.render.approx_age(age)
    else:
        return "", ""


@decorate_inv_paint
def inv_paint_bool(value):
    if value == None:
        return "", ""
    return "", (_("Yes") if value else _("No"))


@decorate_inv_paint
def inv_paint_timestamp_as_age(timestamp):
    age = time.time() - timestamp
    return inv_paint_age(age)


@decorate_inv_paint
def inv_paint_timestamp_as_age_days(timestamp):
    def round_to_day(ts):
        broken = time.localtime(ts)
        return int(time.mktime((broken.tm_year, broken.tm_mon, broken.tm_mday, 0, 0, 0, broken.tm_wday, broken.tm_yday, broken.tm_isdst)))

    now_day = round_to_day(time.time())
    change_day = round_to_day(timestamp)
    age_days = (now_day - change_day) / 86400

    css_class = "number"
    if age_days == 0:
        return css_class, _("today")
    elif age_days == 1:
        return css_class, _("yesterday")
    else:
        return css_class, "%d %s ago" % (int(age_days), _("days"))


@decorate_inv_paint
def inv_paint_docker_labels(labels):
    if labels is None:
        return "", ""

    return "labels", html.render_br().join(sorted(labels.split(", ")))

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
        parts = invpath_parts[:star_index] + ["*"] + invpath_parts[star_index+1:]
        invpath_with_star = "%s" % ".".join(parts)
        candidates.append(invpath_with_star)
        star_index -= 1

    for candidate in candidates:
        # TODO: Better cleanup trailing ":" and "." from display hints at all. They are useless
        # for finding the right entry.
        if candidate in inventory_displayhints:
            return candidate

        if candidate+"." in inventory_displayhints:
            return candidate+"."

        if candidate+":" in inventory_displayhints:
            return candidate+":"

    return None


def _convert_display_hint(hint):
    """Convert paint type to paint function, for the convenciance of the called"""
    if "paint" in hint:
        paint_function_name = "inv_paint_" + hint["paint"]
        hint["paint_function"] = globals()[paint_function_name]

    return hint


def inv_titleinfo(invpath, node):
    hint = _inv_display_hint(invpath)
    icon = hint.get("icon")
    if "title" in hint:
        title = hint["title"]
        if type(title) == type(lambda: None):
            title = title(node)
    else:
        title = invpath.rstrip(".").rstrip(':').split('.')[-1].split(':')[-1].replace("_", " ").title()
    return icon, title


# The titles of the last two path components of the node, e.g. "BIOS / Vendor"
def inv_titleinfo_long(invpath, node):
    icon, last_title = inv_titleinfo(invpath, node)
    parent = inventory.parent_path(invpath)
    if parent:
        icon, parent_title = inv_titleinfo(parent, None)
        return parent_title + u" ➤ " + last_title
    else:
        return last_title


inventory_displayhints.update({
    "."                                                : { "title" : _("Inventory") },
    ".hardware."                                       : { "title" : _("Hardware"), "icon" : "hardware", },
    ".hardware.bios."                                  : { "title" : _("BIOS"), },
    ".hardware.bios.vendor"                            : { "title" : _("Vendor"), },
    ".hardware.bios.version"                           : { "title" : _("Version"), },
    ".hardware.bios.date"                              : { "title" : _("Date"), "paint": "date"},
    ".hardware.chassis."                               : { "title" : _("Chassis"), },
    ".hardware.cpu."                                   : { "title" : _("Processor"), },
    ".hardware.cpu.model"                              : { "title" : _("Model"), "short" : _("CPU Model"), },
    ".hardware.cpu.cache_size"                         : { "title" : _("Cache Size"),                     "paint" : "bytes" },
    ".hardware.cpu.max_speed"                          : { "title" : _("Maximum Speed"),                  "paint" : "hz" },
    ".hardware.cpu.bus_speed"                          : { "title" : _("Bus Speed"),                      "paint" : "hz" },
    ".hardware.cpu.voltage"                            : { "title" : _("Voltage"),                        "paint" : "volt" },
    ".hardware.cpu.cores_per_cpu"                      : { "title" : _("Cores per CPU"),                  "paint" : "count" },
    ".hardware.cpu.threads_per_cpu"                    : { "title" : _("Hyperthreads per CPU"),           "paint" : "count" },
    ".hardware.cpu.threads"                            : { "title" : _("Total Number of Hyperthreads"),   "paint" : "count" },
    ".hardware.cpu.cpus"                               : { "title" : _("Total Number of CPUs"),  "short" : _("CPUs"),  "paint" : "count" },
    ".hardware.cpu.arch"                               : { "title" : _("CPU Architecture"),  "short" : _("CPU Arch"), },
    ".hardware.cpu.cores"                              : { "title" : _("Total Number of Cores"), "short" : _("Cores"), "paint" : "count" },
    ".hardware.memory."                                : { "title" : _("Memory (RAM)"), },
    ".hardware.memory.total_ram_usable"                : { "title" : _("Total usable RAM"),               "paint" : "bytes_rounded" },
    ".hardware.memory.total_swap"                      : { "title" : _("Total swap space"),               "paint" : "bytes_rounded" },
    ".hardware.memory.total_vmalloc"                   : { "title" : _("Virtual addresses for mapping"),  "paint" : "bytes_rounded" },
    ".hardware.memory.arrays:"                         : { "title" : _("Arrays (Controllers)") },
    ".hardware.memory.arrays:*."                       : { "title" : _("Controller %d") },
    ".hardware.memory.arrays:*.devices:"               : { "title" : _("Devices"),
                                                           "keyorder" : [ "locator", "bank_locator", "type", "form_factor", "speed",
                                                                          "data_width", "total_width", "manufacturer", "serial" ]},
    ".hardware.memory.arrays:*.maximum_capacity"       : { "title" : _("Maximum Capacity"),       "paint" : "bytes" },
    ".hardware.memory.arrays:*.devices:*."             : { "title" : lambda v: v["locator"], },
    ".hardware.memory.arrays:*.devices:*.size"         : { "title" : _("Size"),                   "paint" : "bytes", },
    ".hardware.memory.arrays:*.devices:*.speed"        : { "title" : _("Speed"),                  "paint" : "hz", },

    ".hardware.system."                                : { "title" : _("System") },
    ".hardware.system.product"                         : { "title" : _("Product") },
    ".hardware.system.serial"                          : { "title" : _("Serial Number") },
    ".hardware.system.expresscode"                     : { "title" : _("Express Servicecode") },
    ".hardware.system.model"                           : { "title" : _("Model Name") },
    ".hardware.system.manufacturer"                    : { "title" : _("Manufacturer") },

    # Legacy ones. Kept to not break existing views - DON'T use these values for new plugins
    ".hardware.system.serial_number"                   : { "title" : _("Serial Number - LEGACY, don't use") },
    ".hardware.system.model_name"                      : { "title" : _("Model Name - LEGACY, don't use") },

    ".hardware.components."                            : { "title" : _("Physical Components") },
    ".hardware.components.others:"                     : { "title" : _("Other entities"),
                                                            "keyorder" : [ "index", "name", "description", "software", "serial", "manufacturer", "model", "location" ],
                                                            "view" : "invother_of_host" },
    ".hardware.components.others:*.index"              : { "title" : _("Index") },
    ".hardware.components.others:*.name"               : { "title" : _("Name") },
    ".hardware.components.others:*.description"        : { "title" : _("Description") },
    ".hardware.components.others:*.software"           : { "title" : _("Software") },
    ".hardware.components.others:*.serial"             : { "title" : _("Serial Number") },
    ".hardware.components.others:*.manufacturer"       : { "title" : _("Manufacturer") },
    ".hardware.components.others:*.model"              : { "title" : _("Model Name") },
    ".hardware.components.others:*.location"           : { "title" : _("Location") },

    ".hardware.components.unknowns:"                   : { "title" : _("Unknown entities"),
                                                          "keyorder" : [ "index", "name", "description", "software", "serial", "manufacturer", "model", "location" ],
                                                          "view" : "invunknown_of_host" },
    ".hardware.components.unknowns:*.index"            : { "title" : _("Index") },
    ".hardware.components.unknowns:*.name"             : { "title" : _("Name") },
    ".hardware.components.unknowns:*.description"      : { "title" : _("Description") },
    ".hardware.components.unknowns:*.software"         : { "title" : _("Software") },
    ".hardware.components.unknowns:*.serial"           : { "title" : _("Serial Number") },
    ".hardware.components.unknowns:*.manufacturer"     : { "title" : _("Manufacturer") },
    ".hardware.components.unknowns:*.model"            : { "title" : _("Model Name") },
    ".hardware.components.unknowns:*.location"         : { "title" : _("Location") },

    ".hardware.components.chassis:"                    : { "title" : _("Chassis"),
                                                           "keyorder" : [ "index", "name", "description", "software", "serial", "manufacturer", "model", "location" ],
                                                           "view" : "invchassis_of_host" },
    ".hardware.components.chassis:*.index"             : { "title" : _("Index") },
    ".hardware.components.chassis:*.name"              : { "title" : _("Name") },
    ".hardware.components.chassis:*.description"       : { "title" : _("Description") },
    ".hardware.components.chassis:*.software"          : { "title" : _("Software") },
    ".hardware.components.chassis:*.serial"            : { "title" : _("Serial Number") },
    ".hardware.components.chassis:*.manufacturer"      : { "title" : _("Manufacturer") },
    ".hardware.components.chassis:*.model"             : { "title" : _("Model Name") },
    ".hardware.components.chassis:*.location"          : { "title" : _("Location") },

    ".hardware.components.backplanes:"                 : { "title" : _("Backplanes"),
                                                           "keyorder" : [ "index", "name", "description", "software", "serial", "manufacturer", "model", "location" ],
                                                           "view" : "invbackplane_of_host" },
    ".hardware.components.backplanes:*.index"          : { "title" : _("Index") },
    ".hardware.components.backplanes:*.name"           : { "title" : _("Name") },
    ".hardware.components.backplanes:*.description"    : { "title" : _("Description") },
    ".hardware.components.backplanes:*.software"       : { "title" : _("Software") },
    ".hardware.components.backplanes:*.serial"         : { "title" : _("Serial Number") },
    ".hardware.components.backplanes:*.manufacturer"   : { "title" : _("Manufacturer") },
    ".hardware.components.backplanes:*.model"          : { "title" : _("Model Name") },
    ".hardware.components.backplanes:*.location"       : { "title" : _("Location") },

    ".hardware.components.containers:"                 : { "title" : _("Containers"),
                                                           "keyorder" : [ "index", "name", "description", "software", "serial", "manufacturer", "model", "location" ],
                                                           "view" : "invcontainer_of_host" },
    ".hardware.components.containers:*.index"          : { "title" : _("Index") },
    ".hardware.components.containers:*.name"           : { "title" : _("Name") },
    ".hardware.components.containers:*.description"    : { "title" : _("Description") },
    ".hardware.components.containers:*.software"       : { "title" : _("Software") },
    ".hardware.components.containers:*.serial"         : { "title" : _("Serial Number") },
    ".hardware.components.containers:*.manufacturer"   : { "title" : _("Manufacturer") },
    ".hardware.components.containers:*.model"          : { "title" : _("Model Name") },
    ".hardware.components.containers:*.location"       : { "title" : _("Location") },

    ".hardware.components.psus:"                       : { "title" : _("Power Supplies"),
                                                           "keyorder" : [ "index", "name", "description", "software", "serial", "manufacturer", "model", "location" ],
                                                           "view" : "invpsu_of_host" },
    ".hardware.components.psus:*.index"                : { "title" : _("Index") },
    ".hardware.components.psus:*.name"                 : { "title" : _("Name") },
    ".hardware.components.psus:*.description"          : { "title" : _("Description") },
    ".hardware.components.psus:*.software"             : { "title" : _("Software") },
    ".hardware.components.psus:*.serial"               : { "title" : _("Serial Number") },
    ".hardware.components.psus:*.manufacturer"         : { "title" : _("Manufacturer") },
    ".hardware.components.psus:*.model"                : { "title" : _("Model Name") },
    ".hardware.components.psus:*.location"             : { "title" : _("Location") },

    ".hardware.components.fans:"                       : { "title" : _("Fans"),
                                                           "keyorder" : [ "index", "name", "description", "software", "serial", "manufacturer", "model", "location" ],
                                                           "view" : "invfan_of_host" },
    ".hardware.components.fans:*.index"                : { "title" : _("Index") },
    ".hardware.components.fans:*.name"                 : { "title" : _("Name") },
    ".hardware.components.fans:*.description"          : { "title" : _("Description") },
    ".hardware.components.fans:*.software"             : { "title" : _("Software") },
    ".hardware.components.fans:*.serial"               : { "title" : _("Serial Number") },
    ".hardware.components.fans:*.manufacturer"         : { "title" : _("Manufacturer") },
    ".hardware.components.fans:*.model"                : { "title" : _("Model Name") },
    ".hardware.components.fans:*.location"             : { "title" : _("Location") },

    ".hardware.components.sensors:"                    : { "title" : _("Sensors"),
                                                           "keyorder" : [ "index", "name", "description", "software", "serial", "manufacturer", "model", "location" ],
                                                           "view" : "invsensor_of_host" },
    ".hardware.components.sensors:*.index"             : { "title" : _("Index") },
    ".hardware.components.sensors:*.name"              : { "title" : _("Name") },
    ".hardware.components.sensors:*.description"       : { "title" : _("Description") },
    ".hardware.components.sensors:*.software"          : { "title" : _("Software") },
    ".hardware.components.sensors:*.serial"            : { "title" : _("Serial Number") },
    ".hardware.components.sensors:*.manufacturer"      : { "title" : _("Manufacturer") },
    ".hardware.components.sensors:*.model"             : { "title" : _("Model Name") },
    ".hardware.components.sensors:*.location"          : { "title" : _("Location") },

    ".hardware.components.modules:"                    : { "title" : _("Modules"),
                                                           "keyorder" : [ "index", "name", "description", "software", "serial", "model",
                                                                          "manufacturer", "bootloader", "firmware", "type", "location" ],
                                                           "view" : "invmodule_of_host" },
    ".hardware.components.modules:*.index"             : { "title" : _("Index") },
    ".hardware.components.modules:*.name"              : { "title" : _("Name") },
    ".hardware.components.modules:*.description"       : { "title" : _("Description") },
    ".hardware.components.modules:*.software"          : { "title" : _("Software") },
    ".hardware.components.modules:*.serial"            : { "title" : _("Serial Number") },
    ".hardware.components.modules:*.model"             : { "title" : _("Model Name") },
    ".hardware.components.modules:*.manufacturer"      : { "title" : _("Manufacturer") },
    ".hardware.components.modules:*.bootloader"        : { "title" : _("Bootloader") },
    ".hardware.components.modules:*.firmware"          : { "title" : _("Firmware") },
    ".hardware.components.modules:*.type"              : { "title" : _("Type") },
    ".hardware.components.modules:*.location"          : { "title" : _("Location") },

    ".hardware.components.stacks:"                     : { "title" : _("Stacks"),
                                                            "keyorder" : [ "index", "name", "description", "software", "serial", "model", "location" ],
                                                            "view" : "invstack_of_host" },
    ".hardware.components.stacks:*.index"              : { "title" : _("Index") },
    ".hardware.components.stacks:*.name"               : { "title" : _("Name") },
    ".hardware.components.stacks:*.description"        : { "title" : _("Description") },
    ".hardware.components.stacks:*.software"           : { "title" : _("Software") },
    ".hardware.components.stacks:*.serial"             : { "title" : _("Serial Number") },
    ".hardware.components.stacks:*.manufacturer"       : { "title" : _("Manufacturer") },
    ".hardware.components.stacks:*.model"              : { "title" : _("Model Name") },
    ".hardware.components.stacks:*.location"           : { "title" : _("Location") },

    ".hardware.storage."                               : { "title" : _("Storage") },
    ".hardware.storage.controller."                    : { "title" : _("Controller") },
    ".hardware.storage.controller.version"             : { "title" : _("Version") },
    ".hardware.storage.disks:"                         : { "title" : _("Block Devices"), },
    ".hardware.storage.disks:*."                       : { "title" : _("Block Device %d") },
    ".hardware.storage.disks:*.signature"              : { "title" : _("Disk ID") },
    ".hardware.storage.disks:*.vendor"                 : { "title" : _("Vendor") },
    ".hardware.storage.disks:*.local"                  : { "title" : _("Local") },
    ".hardware.storage.disks:*.bus"                    : { "title" : _("Bus") },
    ".hardware.storage.disks:*.product"                : { "title" : _("Product") },
    ".hardware.storage.disks:*.fsnode"                 : { "title" : _("Filesystem Node") },
    ".hardware.storage.disks:*.serial"                 : { "title" : _("Serial Number") },
    ".hardware.storage.disks:*.size"                   : { "title" : _("Size"), "paint" : "size" },
    ".hardware.storage.disks:*.type"                   : { "title" : _("Type") },
    ".hardware.video:"                                 : { "title" : _("Graphic Cards") },
    ".hardware.video:*."                               : { "title" : _("Graphic Card %d") },
    ".hardware.video:*.name"                           : { "title" : _("Graphic Card Name"), "short" : _("Card Name") },
    ".hardware.video:*.subsystem"                      : { "title" : _("Vendor and Device ID"), "short" : _("Vendor") },
    ".hardware.video:*.driver"                         : { "title" : _("Driver"), "short" : _("Driver") },
    ".hardware.video:*.driver_date"                    : { "title" : _("Driver Date"), "short" : _("Driver Date") },
    ".hardware.video:*.driver_version"                 : { "title" : _("Driver Version"), "short" : _("Driver Version") },
    ".hardware.video:*.graphic_memory"                 : { "title" : _("Memory"), "paint" : "bytes_rounded" },

    ".hardware.nwadapter:"                             : { "title" : _("Network Adapters"), },
    ".hardware.nwadapter:*."                           : { "title" : _("Network Adapter %d"), },
    ".hardware.nwadapter:*.name"                       : { "title" : _("Name"), },
    ".hardware.nwadapter:*.type"                       : { "title" : _("Type"), },
    ".hardware.nwadapter:*.macaddress"                 : { "title" : _("Physical Address (MAC)"), },
    ".hardware.nwadapter:*.speed"                      : { "title" : _("Speed"), "paint" : "nic_speed", },
    ".hardware.nwadapter:*.ipv4_address"               : { "title" : _("IPv4 Address"), },
    ".hardware.nwadapter:*.ipv4_subnet"                : { "title" : _("IPv4 Subnet"), },
    ".hardware.nwadapter:*.ipv6_address"               : { "title" : _("IPv6 Address"), },
    ".hardware.nwadapter:*.ipv6_subnet"                : { "title" : _("IPv6 Subnet"), },
    ".hardware.nwadapter:*.gateway"                    : { "title" : _("Gateway"), },

    ".software."                                       : { "title" : _("Software"), "icon" : "software" },
    ".software.os."                                    : { "title" : _("Operating System") },
    ".software.os.name"                                : { "title" : _("Name"), "short" : _("Operating System") },
    ".software.os.version"                             : { "title" : _("Version"), },
    ".software.os.vendor"                              : { "title" : _("Vendor"), },
    ".software.os.type"                                : { "title" : _("Type"), }, # e.g. "linux"
    ".software.os.install_date"                        : { "title" : _("Install Date"), "paint" : "date" },
    ".software.os.kernel_version"                      : { "title" : _("Kernel Version"), "short" : _("Kernel") },
    ".software.os.arch"                                : { "title" : _("Kernel Architecture"), "short" : _("Architecture") },
    ".software.os.service_pack"                        : { "title" : _("Latest Service Pack"), "short" : _("Service Pack") },
    ".software.os.service_packs:"                      : { "title" : _("Service Packs"),
                                                            "keyorder" : [ "name" ] },
    ".software.configuration."                         : { "title" : _("Configuration"), },
    ".software.configuration.snmp_info."               : { "title" : _("SNMP Information"), },
    ".software.configuration.snmp_info.contact"        : { "title" : _("Contact"), },
    ".software.configuration.snmp_info.location"       : { "title" : _("Location"), },
    ".software.configuration.snmp_info.name"           : { "title" : _("System name"), },
    ".software.packages:"                              : { "title" : _("Packages"), "icon" : "packages",
                                                           "keyorder" : [ "name", "version", "arch", "package_type", "summary"], "view" : "invswpac_of_host" },
    ".software.packages:*.name"                        : { "title" : _("Name"), },
    ".software.packages:*.arch"                        : { "title" : _("Architecture"), },
    ".software.packages:*.package_type"                : { "title" : _("Type"), },
    ".software.packages:*.summary"                     : { "title" : _("Description"), },
    ".software.packages:*.version"                     : { "title" : _("Version"), "sort" : utils.cmp_version, "filter" : FilterInvtableVersion  },
    ".software.packages:*.vendor"                      : { "title" : _("Publisher"), },
    ".software.packages:*.package_version"             : { "title" : _("Package Version"), "sort" : utils.cmp_version, "filter" : FilterInvtableVersion },
    ".software.packages:*.install_date"                : { "title" : _("Install Date"), "paint" : "date"},
    ".software.packages:*.size"                        : { "title" : _("Size"), "paint" : "count" },
    ".software.packages:*.path"                        : { "title" : _("Path"), },

    ".software.applications."                          : { "title" : _("Applications"), },

    ".software.applications.check_mk."                         : { "title" : _("Check_MK"), },
    ".software.applications.check_mk.cluster.is_cluster"       : { "title"    : _("Cluster host"),
                                                                   "short"    : _("Cluster"),
                                                                   "paint"    : "bool",
                                                                 },
    ".software.applications.check_mk.cluster.nodes:"           : { "title"    : _("Nodes"),},

    ".software.applications.docker.": {
        "icon": "docker",
        "title": "Docker",
        "keyorder": [ "version", "num_containers_total", "num_containers_running", "num_containers_stopped",
                      "num_containers_paused", "num_images", "registry" ],
    },
    ".software.applications.docker.num_containers_total": {
        "title": _("# Containers"),
    },
    ".software.applications.docker.num_containers_running": {
        "title": _("# Containers running"),
    },
    ".software.applications.docker.num_containers_stopped": {
        "title": _("# Containers stopped"),
    },
    ".software.applications.docker.num_containers_paused": {
        "title": _("# Containers paused"),
    },
    ".software.applications.docker.num_images": {
        "title": _("# Images"),
    },

    ".software.applications.docker.images:": {
        "title" : _("Images"),
        "keyorder": ["id", "repository", "tag", "creation", "size", "labels", "amount_containers"],
        "view" : "invdockerimages_of_host",
    },
    ".software.applications.docker.images:*.id": {
        "title" : _("ID"),
    },
    ".software.applications.docker.images:*.labels": {
        "paint" : "docker_labels",
    },
    ".software.applications.docker.images:*.amount_containers" : {
        "title" : _("# Containers"),
    },

    # Node containers
    ".software.applications.docker.containers:": {
        "title" : _("Containers"),
        "keyorder": ["id", "repository", "tag", "creation", "name", "creation", "labels", "status"],
        "view" : "invdockercontainers_of_host",
    },
    ".software.applications.docker.containers:*.id": {
        "title" : _("ID"),
    },
    ".software.applications.docker.containers:*.labels": {
        "paint" : "docker_labels",
    },

    ".software.applications.docker.networks.*.": {
        "title": "Network %s",
    },
    ".software.applications.docker.networks.*.network_id": {
        "title": "Network ID",
    },

    ".software.applications.docker.container.": {
        "title" : _("Container"),
    },
    ".software.applications.docker.container.node_name": {
        "title" : _("Node name"),
    },
    ".software.applications.docker.container.ports:": {
        "title" : _("Ports"),
        "keyorder" : [ "port", "protocol", "host_addresses" ],
    },

    ".software.applications.docker.container.networks:": {
        "title" : _("Networks"),
        "keyorder" : [ "name", "ip_address", "ip_prefixlen", "gateway",
                       "mac_address", "network_id" ],
    },
    ".software.applications.docker.container.networks:*.ip_address": {
        "title" : _("IP address"),
    },
    ".software.applications.docker.container.networks:*.ip_prefixlen": {
        "title" : _("IP Prefix"),
    },
    ".software.applications.docker.container.networks:*.mac_address": {
        "title" : _("MAC address"),
    },
    ".software.applications.docker.container.networks:*.network_id": {
        "title" : _("Network ID"),
    },

    ".software.applications.docker.networks.*.containers:": {
        "keyorder" : [ "name", "id", "ipv4_address", "ipv6_address", "mac_address" ],
    },
    ".software.applications.docker.networks.*.containers:*.id": {
        "title" : _("ID"),
    },
    ".software.applications.docker.networks.*.containers:*.ipv4_address": {
        "title" : _("IPv4 address"),
    },
    ".software.applications.docker.networks.*.containers:*.ipv6_address": {
        "title" : _("IPv6 address"),
    },
    ".software.applications.docker.networks.*.containers:*.mac_address": {
        "title" : _("MAC address"),
    },

    ".software.applications.citrix."                              : { "title" : _("Citrix") },
    ".software.applications.citrix.controller."                   : { "title" : _("Controller") },
    ".software.applications.citrix.controller.controller_version" : { "title" : _("Controller Version"), },
    ".software.applications.citrix.vm."                           : { "title" : _("Virtual Machine") },
    ".software.applications.citrix.vm.desktop_group_name"         : { "title" : _("Desktop Group Name"), },
    ".software.applications.citrix.vm.catalog"                    : { "title" : _("Catalog"), },
    ".software.applications.citrix.vm.agent_version"              : { "title" : _("Agent Version"), },

    ".software.applications.oracle." : { "title" : _("Oracle DB") },

    ".software.applications.oracle.instance:"                   : { "title"    : _("Instances"),
                                                                    "keyorder" : [ "sid", "version", "openmode", "logmode",
                                                                                   "logins", "db_uptime", "db_creation_time" ],
                                                                    "view"     : "invorainstance_of_host" },
    ".software.applications.oracle.instance:*.sid"              : { "title" : _("SID"), },
    ".software.applications.oracle.instance:*.version"          : { "title" : _("Version"), },
    ".software.applications.oracle.instance:*.openmode"         : { "title" : _("Open mode"), },
    ".software.applications.oracle.instance:*.logmode"          : { "title" : _("Log mode"), },
    ".software.applications.oracle.instance:*.logins"           : { "title" : _("Logins"), },
    ".software.applications.oracle.instance:*.db_uptime"        : { "title" : _("Uptime"), "paint" : "age" },
    ".software.applications.oracle.instance:*.db_creation_time" : { "title" : _("Creation time"), "paint" : "date_and_time" },

    ".software.applications.oracle.dataguard_stats:"             : { "title"    : _("Dataguard statistics"),
                                                                     "keyorder" : [ "sid", "db_unique", "role", "switchover" ],
                                                                     "view"     : "invoradataguardstats_of_host" },
    ".software.applications.oracle.dataguard_stats:*.sid"        : { "title" : _("SID"), },
    ".software.applications.oracle.dataguard_stats:*.db_unique"  : { "title" : _("Name"), },
    ".software.applications.oracle.dataguard_stats:*.role"       : { "title" : _("Role"), },
    ".software.applications.oracle.dataguard_stats:*.switchover" : { "title" : _("Switchover"), },

    ".software.applications.oracle.recovery_area:"            : { "title"    : _("Recovery area"),
                                                                  "keyorder" : [ "sid", "flashback" ],
                                                                  "view"     : "invorarecoveryarea_of_host" },
    ".software.applications.oracle.recovery_area:*.sid"       : { "title" : _("SID"), },
    ".software.applications.oracle.recovery_area:*.flashback" : { "title" : _("Flashback"), },

    ".software.applications.oracle.sga:"                        : { "title"    : _("SGA Info"),
                                                                    "keyorder" : [ "sid", "fixed_size", "redo_buffer", "buf_cache_size",
                                                                                   "in_mem_area_size", "shared_pool_size", "large_pool_size",
                                                                                   "java_pool_size", "streams_pool_size", "shared_io_pool_size",
                                                                                   "data_trans_cache_size", "granule_size", "max_size",
                                                                                   "start_oh_shared_pool", "free_mem_avail" ],
                                                                    "view"     : "invorasga_of_host" },
    ".software.applications.oracle.sga:*.sid"                   : { "title" : _("SID"), },
    ".software.applications.oracle.sga:*.fixed_size"            : { "title" : _("Fixed size"), "paint" : "size" },
    ".software.applications.oracle.sga:*.max_size"              : { "title" : _("Maximum size"), "paint" : "size" },
    ".software.applications.oracle.sga:*.redo_buffer"           : { "title" : _("Redo buffers"), "paint" : "size" },
    ".software.applications.oracle.sga:*.buf_cache_size"        : { "title" : _("Buffer cache size"), "paint" : "size" },
    ".software.applications.oracle.sga:*.in_mem_area_size"      : { "title" : _("In-memory area"), "paint" : "size" },
    ".software.applications.oracle.sga:*.shared_pool_size"      : { "title" : _("Shared pool size"), "paint" : "size" },
    ".software.applications.oracle.sga:*.large_pool_size"       : { "title" : _("Large pool size"), "paint" : "size" },
    ".software.applications.oracle.sga:*.java_pool_size"        : { "title" : _("Java pool size"), "paint" : "size" },
    ".software.applications.oracle.sga:*.streams_pool_size"     : { "title" : _("Streams pool size"), "paint" : "size" },
    ".software.applications.oracle.sga:*.shared_io_pool_size"   : { "title" : _("Shared pool size"), "paint" : "size" },
    ".software.applications.oracle.sga:*.data_trans_cache_size" : { "title" : _("Data transfer cache size"), "paint" : "size" },
    ".software.applications.oracle.sga:*.granule_size"          : { "title" : _("Granule size"), "paint" : "size" },
    ".software.applications.oracle.sga:*.start_oh_shared_pool"  : { "title" : _("Startup overhead in shared pool"), "paint" : "size" },
    ".software.applications.oracle.sga:*.free_mem_avail"        : { "title" : _("Free SGA memory available"), "paint" : "size" },

    ".software.applications.oracle.tablespaces:"                 : { "title"    : _("Tablespaces"),
                                                                     "keyorder" : ["sid", "name", "version", "type", "autoextensible",
                                                                                    "current_size", "max_size", "used_size", "num_increments",
                                                                                    "increment_size", "free_space"],
                                                                     "view"     : "invoratablespace_of_host" },
    ".software.applications.oracle.tablespaces:*.sid"            : { "title" : _("SID"), },
    ".software.applications.oracle.tablespaces:*.name"           : { "title" : _("Name"), },
    ".software.applications.oracle.tablespaces:*.version"        : { "title" : _("Version"), },
    ".software.applications.oracle.tablespaces:*.type"           : { "title" : _("Type"), },
    ".software.applications.oracle.tablespaces:*.autoextensible" : { "title" : _("Autoextensible"), },
    ".software.applications.oracle.tablespaces:*.current_size"   : { "title" : _("Current size"), "paint" : "size" },
    ".software.applications.oracle.tablespaces:*.max_size"       : { "title" : _("Max. size"), "paint" : "size" },
    ".software.applications.oracle.tablespaces:*.used_size"      : { "title" : _("Used size"), "paint" : "size" },
    ".software.applications.oracle.tablespaces:*.num_increments" : { "title" : _("Number of increments"), },
    ".software.applications.oracle.tablespaces:*.increment_size" : { "title" : _("Increment size"), "paint" : "size" },
    ".software.applications.oracle.tablespaces:*.free_space"     : { "title" : _("Free space"), "paint" : "size" },

    ".software.applications.vmwareesx:*."              : { "title" : _("Datacenter %d") },
    ".software.applications.vmwareesx:*.clusters:*."   : { "title" : _("Cluster %d") },

    ".software.applications.mssql."                    : { "title" : _("MSSQL") },
    ".software.applications.mssql.instances:"          : { "title" : _("Instances"),
                                                           "keyorder" : [ "name", "product", "edition", "version", "clustered",
                                                                          "cluster_name", "active_node", "node_names" ],
                                                         },
    ".software.applications.mssql.instances:*.clustered" : { "title" : _("Clustered"), "paint" : "mssql_is_clustered"},

    ".networking."                                     : { "title" : _("Networking"), "icon" : "networking" },
    ".networking.total_interfaces"                     : { "title" : _("Interfaces"), "paint" : "count", },
    ".networking.total_ethernet_ports"                 : { "title" : _("Ports"), "paint" : "count", },
    ".networking.available_ethernet_ports"             : { "title" : _("Ports available"), "paint" : "count", },
    ".networking.addresses:"                           : { "title" : _("IP Addresses"),
                                                           "keyorder" : [ "address", "device", "type" ], },
    ".networking.addresses:*.address"                  : { "title" : _("Address") },
    ".networking.addresses:*.device"                   : { "title" : _("Device") },
    ".networking.addresses:*.type"                     : { "title" : _("Address Type"), "paint" : "ip_address_type" },
    ".networking.routes:"                              : { "title" : _("Routes"),
                                                           "keyorder" : [ "target", "device", "type", "gateway" ] },
    ".networking.routes:*.target"                      : { "title" : _("Target"), "paint" : "ipv4_network" },
    ".networking.routes:*.device"                      : { "title" : _("Device") },
    ".networking.routes:*.type"                        : { "title" : _("Type of route"), "paint" : "route_type" },
    ".networking.routes:*.gateway"                     : { "title" : _("Gateway") },
    ".networking.interfaces:"                          : { "title" : _("Interfaces"),
                                                           "keyorder" : [ "index", "description", "alias", "oper_status", "admin_status", "available", "speed" ],
                                                           "view" : "invinterface_of_host", },
    ".networking.interfaces:*.index"                   : { "title" : _("Index"), "paint" : "number", "filter" : FilterInvtableIDRange },
    ".networking.interfaces:*.description"             : { "title" : _("Description") },
    ".networking.interfaces:*.alias"                   : { "title" : _("Alias") },
    ".networking.interfaces:*.phys_address"            : { "title" : _("Physical Address (MAC)")  },
    ".networking.interfaces:*.oper_status"             : { "title" : _("Operational Status"), "short" : _("Status"), "paint" : "if_oper_status", "filter" : FilterInvtableOperStatus },
    ".networking.interfaces:*.admin_status"            : { "title" : _("Administrative Status"), "short" : _("Admin"), "paint" : "if_admin_status", "filter" : FilterInvtableAdminStatus },
    ".networking.interfaces:*.available"               : { "title" : _("Port Usage"), "short" : _("Used"), "paint" : "if_available", "filter" : FilterInvtableAvailable },
    ".networking.interfaces:*.speed"                   : { "title" : _("Speed"), "paint" : "nic_speed", },
    ".networking.interfaces:*.port_type"               : { "title" : _("Type"), "paint" : "if_port_type", "filter" : FilterInvtableInterfaceType },
    ".networking.interfaces:*.last_change"             : { "title" : _("Last Change"), "paint" : "timestamp_as_age_days", "filter" : FilterInvtableTimestampAsAge },
    ".networking.interfaces:*.vlans"                   : { "title" : _("VLANs") },
    ".networking.interfaces:*.vlantype"                : { "title" : _("VLAN type") },

    ".networking.wlan"                                 : { "title" : _("WLAN") },
    ".networking.wlan.controller"                      : { "title" : _("Controller") },
    ".networking.wlan.controller.accesspoints:"        : { "title" : _("Access Points"), "keyorder" : ["name", "group", "ip_addr", "model", "serial", "sys_location"], },
    ".networking.wlan.controller.accesspoints:*.name"         : { "title" : _("Name") },
    ".networking.wlan.controller.accesspoints:*.group"        : { "title" : _("Group") },
    ".networking.wlan.controller.accesspoints:*.ip_addr"      : { "title" : _("IP Address") },
    ".networking.wlan.controller.accesspoints:*.model"        : { "title" : _("Model") },
    ".networking.wlan.controller.accesspoints:*.serial"       : { "title" : _("Serial Number") },
    ".networking.wlan.controller.accesspoints:*.sys_location" : { "title" : _("System Location") },
})


def declare_inventory_columns():
    # create painters for node with a display hint
    for invpath, hint in inventory_displayhints.items():
        if "*" not in invpath:
            datatype = hint.get("paint", "str")
            long_title = inv_titleinfo_long(invpath, None)
            declare_inv_column(invpath, datatype, long_title, hint.get("short", hint["title"]))


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

def create_inv_rows(hostname, invpath, infoname):
    struct_tree = inventory.load_tree(hostname)
    invdata = inventory.get_inventory_data(struct_tree, invpath)
    if invdata is None:
        return []
    entries = []
    for entry in invdata:
        newrow = {}
        for key, value in entry.items():
            newrow[infoname + "_" + key] = value
        entries.append(newrow)
    return entries


def inv_multisite_table(infoname, invpath, columns, add_headers, only_sites, limit, filters):
    # Create livestatus filter for filtering out hosts
    filter_code = ""
    for filt in filters:
        header = filt.filter(infoname)
        if not header.startswith("Sites:"):
            filter_code += header
    host_columns = [ "host_name" ] + list({c
                                           for c in columns
                                           if c.startswith("host_") and c != "host_name"})
    query = "GET hosts\n"
    query += "Columns: " + (" ".join(host_columns)) + "\n"
    query += filter_code

    if config.debug_livestatus_queries \
            and html.output_format == "html" and display_options.enabled(display_options.W):
        html.open_div(class_="livestatus message", onmouseover="this.style.display=\'none\';")
        html.open_tt()
        html.write(query.replace('\n', '<br>\n'))
        html.close_tt()
        html.close_div()

    sites.live().set_only_sites(only_sites)
    sites.live().set_prepend_site(True)
    data = sites.live().query(query)
    sites.live().set_prepend_site(False)
    sites.live().set_only_sites(None)

    headers = [ "site" ] + host_columns

    # Now create big table of all inventory entries of these hosts
    rows = []
    hostnames = [ row[1] for row in data ]
    for row in data:
        site     = row[0]
        hostname = row[1]
        hostrow = dict(zip(headers, row))
        if infoname == "invhist":
            subrows = create_hist_rows(hostname, columns)
        else:
            subrows = create_inv_rows(hostname, invpath, infoname)

        for subrow in subrows:
            subrow.update(hostrow)
            rows.append(subrow)
    return rows

def inv_find_subtable_columns(invpath):
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
    for path, hint in inventory_displayhints.items():
        if path.startswith(invpath + "*."):
            # ".networking.interfaces:*.port_type" -> "port_type"
            columns.append(path.split(".")[-1])

    for key in subtable_hint.get("keyorder", []):
        if key not in columns:
            columns.append(key)

    columns.sort(cmp = lambda a,b: cmp(order.get(a, 999), order.get(b, 999)) or cmp(a,b))
    return columns


def declare_invtable_columns(infoname, invpath, topic):
    for name in inv_find_subtable_columns(invpath):
        sub_invpath = invpath + "*." + name
        hint = inventory_displayhints.get(sub_invpath, {})

        sortfunc = hint.get("sort", cmp)
        if "paint" in hint:
            paint_name = hint["paint"]
            paint_function = globals()["inv_paint_" + paint_name]
        else:
            paint_name = "str"
            paint_function = inv_paint_generic

        # Sync this with declare_inv_column()
        filter_class = hint.get("filter")
        if not filter_class:
            if paint_name == "str":
                filter_class = FilterInvtableText
            # TODO:
            #elif paint_name == "bool":
            #    filter_class = FilterInvtableBool
            else:
                filter_class = FilterInvtableIDRange

        title = inv_titleinfo(sub_invpath, None)[1]

        declare_invtable_column(infoname, name, topic, title,
                           hint.get("short", title), sortfunc, paint_function, filter_class)


def declare_invtable_column(infoname, name, topic, title, short_title,
                            sortfunc, paint_function, filter_class):
    column = infoname + "_" + name
    multisite_painters[column] = {
        "title"   : topic + ": " + title,
        "short"   : short_title,
        "columns" : [ column ],
        "paint"   : lambda row: paint_function(row.get(column)),
        "sorter"  : column,
    }
    multisite_sorters[column] = {
        "title"    : _("Inventory") + ": " + title,
        "columns" : [ column ],
        "cmp"      : lambda a, b: sortfunc(a.get(column), b.get(column))
    }

    cmk.gui.plugins.visuals.inventory.declare_filter(800, filter_class(infoname, name, topic + ": " + title))


# One master function that does all
def declare_invtable_view(infoname, invpath, title_singular, title_plural):

    def inv_table(columns, add_headers, only_sites, limit, filters):
        return inv_multisite_table(infoname, invpath, columns, add_headers, only_sites, limit, filters)

    # Declare the "info" (like a database table)
    cmk.gui.plugins.visuals.declare_info(infoname, {
        'title'       : title_singular,
        'title_plural': title_plural,
        'single_spec' : None,
    })

    # Create the datasource (like a database view)
    multisite_datasources[infoname] = {
        "title"        : "%s: %s" % (_("Inventory"), title_plural),
        "table"        : inv_table,
        "infos"        : [ "host", infoname ],
        "keys"         : [],
        "idkeys"       : [],
    }

    # Declare a painter, sorter and filters for each path with display hint
    declare_invtable_columns(infoname, invpath, title_singular)

    # Create a nice search-view containing these columns
    painters = []
    filters = []
    for name in inv_find_subtable_columns(invpath):
        column = infoname + "_" + name
        painters.append( ( column, '', '' ) )
        filters.append(column)

    # Declare two views: one for searching globally. And one
    # for the items of one host.

    view_spec = {
        'datasource'                   : infoname,
        'topic'                        : _('Inventory'),
        'public'                       : True,
        'layout'                       : 'table',
        'num_columns'                  : 1,
        'browser_reload'               : 0,
        'column_headers'               : 'pergroup',
        'user_sortable'                : True,
        'play_sounds'                  : False,
        'force_checkboxes'             : False,
        'mobile'                       : False,

        'group_painters'               : [],
        'sorters'                      : [],
    }

    # View for searching for items
    multisite_builtin_views[infoname + "_search"] = {
        # General options
        'title'                        : _("Search %s") % title_plural,
        'description'                  : _('A view for searching in the inventory data for %s') % title_plural,
        'hidden'                       : False,
        'mustsearch'                   : True,

        # Columns
        'painters'                     : [ ('host','inv_host', '') ] + painters,

        # Filters
        'show_filters'                 : [
            'siteopt',
            'hostregex',
            'hostgroups',
            'opthostgroup',
            'opthost_contactgroup',
            'host_address',
            'host_tags',
            'hostalias',
            'host_favorites',] + filters,
        'hide_filters' : [ ],
        'hard_filters' : [],
        'hard_filtervars' : [],
    }
    multisite_builtin_views[infoname + "_search"].update(view_spec)

    # View for the items of one host
    multisite_builtin_views[infoname + "_of_host"] = {
        # General options
        'title'                        : title_plural,
        'description'                  : _('A view for the %s of one host') % title_plural,
        'hidden'                       : True,
        'mustsearch'                   : False,

        # Columns
        'painters'                     : painters,

        # Filters
        'show_filters'                 : filters,
        'hard_filters' : [ ],
        'hard_filtervars' : [],
        'hide_filters' : [ "host" ],
    }
    multisite_builtin_views[infoname + "_of_host"].update(view_spec)

    # View enabled checker for the _of_host view
    view_is_enabled[infoname + "_of_host"] = _create_view_enabled_check_func(invpath)


def _create_view_enabled_check_func(invpath):
    def _check_view_enabled(linking_view, view, context_vars):
        context = dict(context_vars)
        if "host" not in context:
            return True # No host data? Keep old behaviour
        if context["host"] == "":
            return False
        struct_tree = inventory.load_tree(context["host"])
        if not struct_tree:
            return False
        if struct_tree.is_empty():
            return False
        parsed_path, unused_key = inventory.parse_tree_path(invpath)
        if parsed_path:
            children = struct_tree.get_sub_children(parsed_path)
        else:
            children = [struct_tree.get_root_container()]
        if children is None:
            return False
        return True
    return _check_view_enabled


# Now declare Multisite views for a couple of embedded tables
declare_invtable_view("invswpac",      ".software.packages:",       _("Software package"),   _("Software packages"))
declare_invtable_view("invinterface",  ".networking.interfaces:",   _("Network interface"),  _("Network interfaces"))

declare_invtable_view("invdockerimages",  ".software.applications.docker.images:",   _("Docker images"),  _("Docker images"))
declare_invtable_view("invdockercontainers",  ".software.applications.docker.containers:",   _("Docker containers"),  _("Docker containers"))

declare_invtable_view("invother", ".hardware.components.others:", _("Other entity"), _("Other entities"))
declare_invtable_view("invunknown", ".hardware.components.unknowns:", _("Unknown entity"), _("Unknown entities"))
declare_invtable_view("invchassis", ".hardware.components.chassis:", _("Chassis"), _("Chassis"))
declare_invtable_view("invbackplane", ".hardware.components.backplanes:", _("Backplane"), _("Backplanes"))
declare_invtable_view("invcontainer", ".hardware.components.containers:", _("HW container"), _("HW containers"))
declare_invtable_view("invpsu", ".hardware.components.psus:", _("Power supply"), _("Power supplies"))
declare_invtable_view("invfan", ".hardware.components.fans:", _("Fan"), _("Fans"))
declare_invtable_view("invsensor", ".hardware.components.sensors:", _("Sensor"), _("Sensors"))
declare_invtable_view("invmodule", ".hardware.components.modules:", _("Module"), _("Modules"))
declare_invtable_view("invstack", ".hardware.components.stacks:", _("Stack"), _("Stacks"))

declare_invtable_view("invorainstance",       ".software.applications.oracle.instance:",        _("Oracle instance"),            _("Oracle instances"))
declare_invtable_view("invorarecoveryarea",   ".software.applications.oracle.recovery_area:",   _("Oracle recovery area"),       _("Oracle recovery areas"))
declare_invtable_view("invoradataguardstats", ".software.applications.oracle.dataguard_stats:", _("Oracle dataguard statistic"), _("Oracle dataguard statistics"))
declare_invtable_view("invoratablespace",     ".software.applications.oracle.tablespaces:",     _("Oracle tablespace"),          _("Oracle tablespaces"))
declare_invtable_view("invorasga",            ".software.applications.oracle.sga:",             _("Oracle performance"),         _("Oracle performance"))


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
    'datasource'                   : 'hosts',
    'topic'                        : _('Inventory'),
    'title'                        : _('Inventory of host'),
    'linktitle'                    : _('Inventory'),
    'description'                  : _('The complete hardware- and software inventory of a host'),
    'icon'                         : 'inv',
    'hidebutton'                   : False,
    'public'                       : True,
    'hidden'                       : True,

    # Layout options
    'layout'                       : 'dataset',
    'num_columns'                  : 1,
    'browser_reload'               : 0,
    'column_headers'               : 'pergroup',
    'user_sortable'                : False,
    'play_sounds'                  : False,
    'force_checkboxes'             : False,
    'mustsearch'                   : False,
    'mobile'                       : False,

    # Columns
    'group_painters'               : [],
    'painters'                     : [
            ('host',           'host', ''),
            ('inv',            None,   ''),
    ],

    # Filters
    'hard_filters'                 : [],
    'hard_filtervars'              : [],
    'hide_filters'                 : ['host', 'site'],
    'show_filters'                 : [],
    'sorters'                      : [],
}

view_is_enabled["inv_host"] = _create_view_enabled_check_func(".")

generic_host_filters = multisite_builtin_views["allhosts"]["show_filters"]

# View with table of all hosts, with some basic information
multisite_builtin_views["inv_hosts_cpu"] = {
    # General options
    'datasource'                   : 'hosts',
    'topic'                        : _('Inventory'),
    'title'                        : _('CPU Related Inventory of all Hosts'),
    'linktitle'                    : _('CPU Inv. (all Hosts)'),
    'description'                  : _('A list of all hosts with some CPU related inventory data'),
    'public'                       : True,
    'hidden'                       : False,

    # Layout options
    'layout'                       : 'table',
    'num_columns'                  : 1,
    'browser_reload'               : 0,
    'column_headers'               : 'pergroup',
    'user_sortable'                : True,
    'play_sounds'                  : False,
    'force_checkboxes'             : False,
    'mustsearch'                   : False,
    'mobile'                       : False,

    # Columns
    'group_painters'               : [],
    'painters'                     : [
         ('host',                       'inv_host', ''),
         ('inv_software_os_name',       None,   ''),
         ('inv_hardware_cpu_cpus',      None,   ''),
         ('inv_hardware_cpu_cores',     None,   ''),
         ('inv_hardware_cpu_max_speed', None,   ''),
         ('perfometer',                 None, '', 'CPU load'),
         ('perfometer',                 None, '', 'CPU utilization'),

    ],

    # Filters
    'hard_filters'                 : [
        'has_inv'
    ],
    'hard_filtervars'              : [
        ('is_has_inv', '1' ),
    ],
    'hide_filters'                 : [],
    'show_filters'                 : [
         'inv_hardware_cpu_cpus',
         'inv_hardware_cpu_cores',
         'inv_hardware_cpu_max_speed',
     ],
    'sorters'                      : [],
}


# View with available and used ethernet ports
multisite_builtin_views["inv_hosts_ports"] = {
    # General options
    'datasource'                   : 'hosts',
    'topic'                        : _('Inventory'),
    'title'                        : _('Switch port statistics'),
    'linktitle'                    : _('Switch ports (all Hosts)'),
    'description'                  : _('A list of all hosts with statistics about total, used and free networking interfaces'),
    'public'                       : True,
    'hidden'                       : False,

    # Layout options
    'layout'                       : 'table',
    'num_columns'                  : 1,
    'browser_reload'               : 0,
    'column_headers'               : 'pergroup',
    'user_sortable'                : True,
    'play_sounds'                  : False,
    'force_checkboxes'             : False,
    'mustsearch'                   : False,
    'mobile'                       : False,

    # Columns
    'group_painters'               : [],
    'painters'                     : [
         ('host',                       'invinterface_of_host', ''),
         ('inv_hardware_system_product',             None, ''),
         ('inv_networking_total_interfaces',         None, ''),
         ('inv_networking_total_ethernet_ports',     None, ''),
         ('inv_networking_available_ethernet_ports', None, ''),
    ],

    # Filters
    'hard_filters'                 : [ 'has_inv' ],
    'hard_filtervars'              : [ ('is_has_inv', '1' ), ],
    'hide_filters'                 : [],
    'show_filters'                 : generic_host_filters + [],
    'sorters'                      : [ ('inv_networking_available_ethernet_ports', True) ],
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


def inv_history_table(columns, add_headers, only_sites, limit, filters):
    return inv_multisite_table("invhist", None, columns, add_headers, only_sites, limit, filters)


def create_hist_rows(hostname, columns):
    for old_timestamp, old_tree, new_tree in inventory.get_history(hostname):
        new, changed, removed, delta_tree = new_tree.compare_with(old_tree)
        newrow = {
            "invhist_time"    : old_timestamp,
            "invhist_delta"   : delta_tree,
            "invhist_removed" : removed,
            "invhist_new"     : new,
            "invhist_changed" : changed,
        }
        yield newrow


multisite_datasources["invhist"] = {
    "title"        : _("Inventory: History"),
    "table"        : inv_history_table,
    "infos"        : [ "host", "invhist" ],
    "keys"         : [],
    "idkeys"       : [ "host_name", "invhist_time" ],
}

multisite_painters["invhist_time"] = {
    "title"    : _("Inventory Date/Time"),
    "short"    : _("Date/Time"),
    "columns"  : [ "invhist_time" ],
    "options"  : [ "ts_format", "ts_date" ],
    "paint"    : lambda row: paint_age(row["invhist_time"], True, 60 * 10),
}

multisite_painters["invhist_delta"] = {
    "title"    : _("Inventory changes"),
    "columns"  : [ "invhist_delta" "invhist_time" ],
    "paint"    : lambda row: paint_host_inventory_tree(row, column="invhist_delta"),
}


def paint_invhist_count(row, what):
    number = row["invhist_" + what]
    if number:
        return "narrow number", str(number)
    else:
        return "narrow number unused", "0"

multisite_painters["invhist_removed"] = {
    "title"    : _("Removed entries"),
    "short"    : _("Removed"),
    "columns"  : [ "invhist_removed" ],
    "paint"    : lambda row: paint_invhist_count(row, "removed"),
}

multisite_painters["invhist_new"] = {
    "title"    : _("new entries"),
    "short"    : _("new"),
    "columns"  : [ "invhist_new" ],
    "paint"    : lambda row: paint_invhist_count(row, "new"),
}

multisite_painters["invhist_changed"] = {
    "title"    : _("changed entries"),
    "short"    : _("changed"),
    "columns"  : [ "invhist_changed" ],
    "paint"    : lambda row: paint_invhist_count(row, "changed"),
}


# sorters
declare_1to1_sorter("invhist_time",    cmp_simple_number, reverse=True)
declare_1to1_sorter("invhist_removed", cmp_simple_number)
declare_1to1_sorter("invhist_new",     cmp_simple_number)
declare_1to1_sorter("invhist_changed", cmp_simple_number)

# View for inventory history of one host

multisite_builtin_views["inv_host_history"] = {
    # General options
    'datasource'                   : 'invhist',
    'topic'                        : _('Inventory'),
    'title'                        : _('Inventory history of host'),
    'linktitle'                    : _('Inventory History'),
    'description'                  : _('The history for changes in hardware- and software inventory of a host'),
    'icon'                         : 'inv',
    'hidebutton'                   : False,
    'public'                       : True,
    'hidden'                       : True,

    # Layout options
    'layout'                       : 'table',
    'num_columns'                  : 1,
    'browser_reload'               : 0,
    'column_headers'               : 'pergroup',
    'user_sortable'                : True,
    'play_sounds'                  : False,
    'force_checkboxes'             : False,
    'mustsearch'                   : False,
    'mobile'                       : False,

    # Columns
    'group_painters'               : [],
    'painters'                     : [
            ('invhist_time',     None,   ''),
            ('invhist_removed',  None,   ''),
            ('invhist_new',      None,   ''),
            ('invhist_changed',  None,   ''),
            ('invhist_delta',    None,   ''),
    ],

    # Filters
    'hard_filters'                 : [],
    'hard_filtervars'              : [],
    'hide_filters'                 : ['host'],
    'show_filters'                 : [],
    'sorters'                      : [('invhist_time', False)],
}

view_is_enabled["inv_host_history"] = _create_view_enabled_check_func(".")

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



class NodeRenderer(object):
    def __init__(self, hostname, tree_id, invpath, show_internal_tree_paths=False):
        self._hostname = hostname
        self._tree_id = tree_id
        self._invpath = invpath
        if show_internal_tree_paths:
            self._show_internal_tree_paths = "on"
        else:
            self._show_internal_tree_paths = ""

    #   ---container------------------------------------------------------------

    def show_container(self, container, path=None):
        for _, node in container.get_edge_nodes():
            node_abs_path = node.get_absolute_path()

            raw_invpath = self._get_raw_path(".".join(map(str, node_abs_path)))
            invpath = ".%s." % raw_invpath

            icon, title = inv_titleinfo(invpath, node)

            # Replace placeholders in title with the real values for this path
            if "%d" in title or "%s" in title:
                title = self._replace_placeholders(title, invpath)

            header = self._get_header(title, ".".join(map(str, node_abs_path)), "#666")
            fetch_url = html.makeuri_contextless([("host", self._hostname),
                                                  ("path", invpath),
                                                  ("show_internal_tree_paths", self._show_internal_tree_paths),
                                                  ("treeid", self._tree_id)],
                                                 "ajax_inv_render_tree.py")

            if html.begin_foldable_container("inv_%s%s" % (self._hostname, self._tree_id), invpath, False,
                                             header, icon=icon, fetch_url=fetch_url, tree_img="tree_black"):
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
        keyorder = hint.get("keyorder", []) # well known keys
        data = numeration.get_child_data()

        # Add titles for those keys
        titles = []
        for key in keyorder:
            sub_invpath = "%s0.%s" % (invpath, key)
            icon, title = inv_titleinfo(sub_invpath, None)
            sub_hint = _inv_display_hint(sub_invpath)
            short_title = sub_hint.get("short", title)
            titles.append((short_title, key))

        # Determine *all* keys, in order to find unknown ones
        keys = self._get_numeration_keys(data)

        # Order not well-known keys alphabetically
        extratitles = []
        for key in keys:
            if key not in keyorder:
                icon, title = inv_titleinfo("%s0.%s" % (invpath, key), None)
                extratitles.append((title, key))
        extratitles.sort()
        titles += extratitles

        # Link to Multisite view with exactly this table
        if "view" in hint:
            url = html.makeuri_contextless([
                ("view_name", hint["view"] ),
                ("host", self._hostname)],
                filename="view.py")
            html.div(html.render_a(_("Open this table for filtering / sorting"), href=url),
                     class_="invtablelink")

        self._show_numeration_table(titles, invpath, data)


    def _get_numeration_keys(self, data):
        keys = set([])
        for entry in data:
            keys.update(entry.keys())
        return keys


    def _show_numeration_table(self, titles, invpath, data):
        # We cannot use table here, since html.plug() does not work recursively
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
                    unused_value = value[1] if type(value) == tuple else value
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

        def _sort_attributes(item):
            """Sort the attributes by the configured key order. In case no key order
            is given sort by the key. In case there is a key order and a key is not
            in the list, put it at the end and sort all of those by key."""
            key = item[0]
            keyorder = hint.get("keyorder")
            if not keyorder:
                return key

            try:
                return keyorder.index(key)
            except ValueError:
                return len(keyorder) + 1, key

        html.open_table()
        for key, value in sorted(attributes.get_child_data().iteritems(), key=_sort_attributes):
            sub_invpath = "%s.%s" % (invpath, key)
            icon, title = inv_titleinfo(sub_invpath, key)
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
        else:
            return path.strip(".")


    def _get_header(self, title, key, hex_color):
        header = HTML(title)
        if self._show_internal_tree_paths:
            header += HTML(" <span style='color: %s'>(%s)</span>" % \
                           (hex_color, key))
        return header


    def _show_child_value(self, value, hint):
        if "paint_function" in hint:
            tdclass, code = hint["paint_function"](value)
            html.write(code)
        elif type(value) == str:
            try:
                text = value.decode("utf-8")
            except:
                text = value
            html.write_text(text)
        elif type(value) == unicode:
            html.write_text(value)
        elif type(value) == int:
            html.write(str(value))
        elif type(value) == float:
            html.write("%.2f" % value)
        elif value != None:
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
        elif old is not None and new is not None:
            html.open_span(class_="invold")
            self._show_child_value(old, hint)
            html.close_span()
            html.write(u" → ")
            html.open_span(class_="invnew")
            self._show_child_value(new, hint)
            html.close_span()
        elif old == new:
            self._show_child_value(old, hint)


# Ajax call for fetching parts of the tree
def ajax_inv_render_tree():
    hostname = html.var("host")
    invpath = html.var("path")
    tree_id = html.var("treeid", "")
    if html.var("show_internal_tree_paths"):
        show_internal_tree_paths = True
    else:
        show_internal_tree_paths = False
    if tree_id:
        struct_tree = inventory.load_delta_tree(hostname, int(tree_id[1:]))
        tree_renderer = DeltaNodeRenderer(hostname, tree_id, invpath)
    else:
        struct_tree = inventory.load_tree(hostname)
        tree_renderer = AttributeRenderer(hostname, "", invpath,
                        show_internal_tree_paths=show_internal_tree_paths)

    if struct_tree is None:
        html.show_error(_("No such inventory tree."))

    struct_tree = struct_tree.get_filtered_tree(inventory.get_permitted_inventory_paths())

    parsed_path, attributes_key = inventory.parse_tree_path(invpath)
    if parsed_path:
        children = struct_tree.get_sub_children(parsed_path)
    else:
        children = [struct_tree.get_root_container()]

    if children is None:
        html.show_error(_("Invalid path in inventory tree: '%s' >> %s") % (invpath, repr(parsed_path)))
    else:
        for child in inventory.sort_children(children):
            child.show(tree_renderer, path=invpath)
