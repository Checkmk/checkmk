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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import inventory

def paint_host_inventory(row, invpath):
    invdata = inventory.get(row["host_inventory"], invpath)
    if not invdata:
        return "", "" # _("No inventory data available")

    hint = inv_display_hint(invpath)
    if "paint_function" in hint:
        return hint["paint_function"](invdata)
    elif invdata == None:
        return "", ""
    elif type(invdata) in ( str, unicode ):
        return "", invdata
    elif not is_leaf_type(invdata):
        return paint_inv_tree(row, invpath)
    else:
        return "number", str(invdata)

def cmp_inventory_node(a, b, invpath):
    val_a = inventory.get(a["host_inventory"], invpath)
    val_b = inventory.get(b["host_inventory"], invpath)
    return cmp(a, b)

inv_filter_info = {
    "bytes"         : { "unit" : _("MB"),    "scale" : 1024*1024 },
    "bytes_rounded" : { "unit" : _("MB"),    "scale" : 1024*1024 },
    "hz"            : { "unit" : _("MHz"),   "scale" : 1000000 },
    "volt"          : { "unit" : _("Volt") },
    "timestamp"     : { "unit" : _("secs") },
}


# Declare all three with one simple call (for simple data types)
def declare_inv_column(invpath, datatype, title, short = None):
    if invpath == ".":
        name = "inv"
    else:
        name = "inv_" + invpath.replace(":", "_").replace(".", "_").strip("_")

    # Declare column painter
    multisite_painters[name] = {
        "title"    : invpath == "." and _("Inventory Tree") or (_("Inventory") + ": " + title),
        "columns"  : [],
        "load_inv" : True,
        "paint"    : lambda row: paint_host_inventory(row, invpath),
        "sorter"   : name,
    }
    if short:
        multisite_painters[name]["short"] = short

    # Sorters and Filters only for leaf nodes
    if invpath[-1] not in ":.":
        # Declare sorter. It will detect numbers automatically
        multisite_sorters[name] = {
            "title"    : _("Inventory") + ": " + title,
            "columns"  : [],
            "load_inv" : True,
            "cmp"      : lambda a, b: cmp_inventory_node(a, b, invpath),
        }

        # Declare filter.
        if datatype == "str":
            visuals.declare_filter(800, visuals.FilterInvText(name, invpath, title))
        else:
            filter_info = inv_filter_info.get(datatype, {})
            visuals.declare_filter(800, visuals.FilterInvFloat(name, invpath, title,
               unit = filter_info.get("unit"),
               scale = filter_info.get("scale", 1.0)))


# Tree painter
def paint_inv_tree(row, invpath = ".", column = "host_inventory"):
    hostname = row["host_name"]
    tree = row[column]
    if column == "host_inventory":
        tree_id = ""
    else:
        tree_id = "/" + str(row["invhist_time"])
    node = inventory.get(tree, invpath)
    html.plug()
    render_inv_subtree_container(hostname, tree_id, invpath, node)
    code = html.drain()
    html.unplug()
    return "invtree", code

def render_inv_subtree(hostname, tree_id, invpath, node):
    if is_leaf_type(node):
        render_inv_subtree_leaf(hostname, tree_id, invpath, node)
    else:
        render_inv_subtree_foldable(hostname, tree_id, invpath, node)

def render_inv_subtree_foldable(hostname, tree_id, invpath, node):
    if node: # omit empty nodes completely
        icon, title = inv_titleinfo(invpath, node)

        if "%d" in title: # Replace with list index
            list_index = int(invpath.split(":")[-1].rstrip(".")) + 1
            title = title % list_index

        fetch_url = html.makeuri_contextless([("host", hostname), ("path", invpath), ("treeid", tree_id)], "ajax_inv_render_tree.py")
        if html.begin_foldable_container("inv_" + hostname + tree_id, invpath, False, title, icon=icon, fetch_url=fetch_url):
            # Render only if it is open. We'll get the stuff via ajax later if it's closed
            render_inv_subtree_container(hostname, tree_id, invpath, node)
        html.end_foldable_container()

def render_inv_subtree_container(hostname, tree_id, invpath, node):
    hint = inv_display_hint(invpath)
    if "render" in hint:
        try:
            hint["render"](hostname, invpath, node)
        except:
            hint["render"](hostname, tree_id, invpath, node)
    elif type(node) == dict:
        render_inv_subtree_dict(hostname, tree_id, invpath, node)
    else:
        render_inv_subtree_list(hostname, tree_id, invpath, node)

def is_leaf_type(value):
    if type(value) in (list, dict):
        return False
    elif type(value) == tuple and type(value[0]) == list: # Delta mode lists
        return False
    else:
        return True

def render_inv_subtree_dict(hostname, tree_id, invpath, node):
    items = node.items()
    items.sort()

    leaf_nodes = []
    for key, value in items:
        if is_leaf_type(value):
            invpath_sub = invpath + key
            icon, title = inv_titleinfo(invpath_sub, value)
            leaf_nodes.append((title, invpath_sub, value))

    if leaf_nodes:
        leaf_nodes.sort()
        html.write("<table>")
        for title, invpath_sub, value in leaf_nodes:
            html.write("<tr><th title='%s'>%s</th><td>" % (invpath_sub, title))
            render_inv_subtree(hostname, tree_id, invpath_sub, value)
            html.write("</td></tr>")
        html.write("</table>")

    non_leaf_nodes = [ item for item in items if not is_leaf_type(item[1]) ]
    non_leaf_nodes.sort()
    for key, value in non_leaf_nodes:
        invpath_sub = invpath + key
        if type(value) == dict:
            invpath_sub += "."
        elif type(value) == list or (type(value) == tuple and type(value[0]) == list):
            invpath_sub += ":"
        render_inv_subtree_foldable(hostname, tree_id, invpath_sub, value)

def render_inv_subtree_list(hostname, tree_id, invpath, node):
    # In delta-mode node is a pair of (removed, new)
    if not node:
        return

    elif type(node) == tuple:
        html.write(_("Removed entries") + ":<br>")
        html.write("<span class=invold>")
        render_inv_subtree_list(hostname, tree_id, invpath, node[0])
        html.write("</span>")

        html.write(_("New entries") + ":<br>")
        html.write("<span class=invnew>")
        render_inv_subtree_list(hostname, tree_id, invpath, node[1])
        html.write("</span>")

    else:
        for nr, value in enumerate(node):
            invpath_sub = invpath + str(nr)
            if type(value) == dict:
                invpath_sub += "."
            elif type(value) == list or (type(value) == tuple and type(value[0]) == list):
                invpath_sub += ":"
            render_inv_subtree(hostname, tree_id, invpath_sub, value)


def render_inv_subtree_leaf(hostname, tree_id, invpath, node):
    # In delta mode node is a pair (old_value, new_value)
    if type(node) == tuple:
        if node[0] == node[1] or node[0] == None:
            if node[0] == None:
                html.write("<span class=invnew>")
            render_inv_subtree_leaf_value(hostname, tree_id, invpath, node[1])
            if node[0] == None:
                html.write("</span>")
        else:
            html.write("<span class=invold>")
            render_inv_subtree_leaf_value(hostname, tree_id, invpath, node[0])
            html.write("</span>")
            html.write(u" → ")
            html.write("<span class=invnew>")
            render_inv_subtree_leaf_value(hostname, tree_id, invpath, node[1])
            html.write("</span>")
    else:
        render_inv_subtree_leaf_value(hostname, tree_id, invpath, node)
    html.write("<br>")

def render_inv_subtree_leaf_value(hostname, tree_id, invpath, node):
    hint = inv_display_hint(invpath)
    if "paint_function" in hint:
        tdclass, code = hint["paint_function"](node)
        html.write(code)
    elif "render" in hint:
        hint["render"](node)
    elif type(node) == str:
        try:
            text = node.decode("utf-8")
        except:
            text = node
        html.write(html.attrencode(node))
    elif type(node) == unicode:
        html.write(html.attrencode(node))
    elif type(node) == int:
        html.write(str(node))
    elif type(node) == float:
        html.write("%.2f" % node)
    elif node != None:
        html.write(str(node))


def render_inv_dicttable(hostname, tree_id, invpath, node):
    # In delta mode node is a pair of (old_items, new_items)
    if type(node) == tuple:
        html.write(_("Removed entries") + ":")
        html.write("<span class=invold>")
        render_inv_dicttable(hostname, tree_id, invpath, node[0])
        html.write("</span>")

        html.write(_("New entries") + ":")
        html.write("<span class=invnew>")
        render_inv_dicttable(hostname, tree_id, invpath, node[1])
        html.write("</span>")
        return

    hint = inv_display_hint(invpath)
    keyorder = hint.get("keyorder", []) # well known keys

    # Add titles for those keys
    titles = []
    for key in keyorder:
        icon, title = inv_titleinfo(invpath + "0." + key, None)
        titles.append((title, key))

    # Determine *all* keys, in order to find unknown ones
    keys = set([])
    for entry in node:
        keys.update(entry.keys())

    # Order not well-known keys alphabetically
    extratitles = []
    for key in keys:
        if key not in keyorder:
            icon, title = inv_titleinfo(invpath + "0." + key, None)
            extratitles.append((title, key))
    extratitles.sort()
    titles += extratitles

    # We cannot use table here, since html.plug() does not work recursively
    html.write('<table class=data>')
    html.write('<tr>')
    for title, key in titles:
        html.write('<th>%s</th>' % title)
    html.write('</tr>')

    for nr, entry in enumerate(node):
        html.write('<tr class=even0>')
        for title, key in titles:
            value = entry.get(key)
            invpath_sub = invpath + "%d.%s" % (nr, key)
            if type(value) == dict:
                invpath_sub += "."
            elif type(value) == list or (type(value) == tuple and type(value[0]) == list):
                invpath_sub += ":"
            html.write('<td>')
            render_inv_subtree(hostname, tree_id, invpath_sub, value)
            html.write('</td>')
        html.write('</tr>')
    html.write('</table>')


# Convert .foo.bar:18.test to .foo.bar:*.test
def inv_display_hint(invpath):
    r = regex(":[0-9]+")
    invpath = r.sub(":*", invpath)
    hint = inventory_displayhints.get(invpath, {})

    # Convert paint type to paint function, for the convenciance of the called
    if "paint" in hint:
        paint_function_name = "inv_paint_" + hint["paint"]
        hint["paint_function"] = globals()[paint_function_name]

    return hint

def inv_titleinfo(invpath, node):
    hint = inv_display_hint(invpath)
    icon = hint.get("icon")
    if "title" in hint:
        title = hint["title"]
        if type(title) == type(lambda: None):
            title = title(node)
    else:
        title = invpath.split('.')[-1].split(':')[-1].replace("_", " ").title()
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


multisite_painters["inventory_tree"] = {
    "title"    : _("Hardware &amp; Software Tree"),
    "columns"  : [],
    "load_inv" : True,
    "paint"    : paint_inv_tree,
}


def inv_paint_hz(hz):
    if hz == None:
        return "", _("unknown")

    if hz < 10:
        return "number", "%.2f" % hz
    elif hz < 100:
        return "number", "%.11" % hz
    elif hz < 1500:
        return "number", "%.0f" % hz
    elif hz < 1000000:
        return "number", "%.1f kHz" % (hz / 1000)
    elif hz < 1000000000:
        return "number", "%.1f MHz" % (hz / 1000000)
    else:
        return "number", "%.2f GHz" % (hz / 1000000000)

def inv_paint_bytes(b):
    if b == None:
        return "", _("unknown")
    elif b == 0:
        return "number", "0"

    units = [ 'B', 'kB', 'MB', 'GB', 'TB' ]
    i = 0
    while b % 1024 == 0 and i+1 < len(units):
        b = b / 1024
        i += 1
    return "number", "%d %s" % (b, units[i])

def inv_paint_count(b):
    if b == None:
        return "", ""
    else:
        return "number", str(b)

def inv_paint_bytes_rounded(b):
    if b == None:
        return "", ""
    elif b == 0:
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

def inv_paint_volt(volt):
    if volt:
        return "number", "%.1f V" % volt
    else:
        return "", ""

def inv_paint_timestamp(stamp):
    if stamp:
        return "Unix time", "%i" % stamp
    else:
        return "", ""

def inv_paint_date(stamp):
    if stamp:
        date_painted = time.strftime("%Y-%m-%d", time.localtime(stamp))
        return "Date", "%s" % date_painted
    else:
        return "", ""

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
    ".hardware.memory.arrays:*.devices:"               : { "title" : _("Devices"), "render" : render_inv_dicttable,
                                                           "keyorder" : [ "locator", "bank_locator", "type", "form_factor", "speed",
                                                                          "data_width", "total_width", "manufacturer", "serial" ]},
    ".hardware.memory.arrays:*.maximum_capacity"       : { "title" : _("Maximum Capacity"),       "paint" : "bytes" },
    ".hardware.memory.arrays:*.devices:*."             : { "title" : lambda v: v["locator"], },
    ".hardware.memory.arrays:*.devices:*.size"         : { "title" : _("Size"),                   "paint" : "bytes", },
    ".hardware.memory.arrays:*.devices:*.speed"        : { "title" : _("Speed"),                  "paint" : "hz", },
    ".hardware.system."                                : { "title" : _("System") },
    ".hardware.storage."                               : { "title" : _("Storage") },
    ".hardware.storage.disks:"                         : { "title" : _("Block Devices") },
    ".hardware.storage.disks:*."                       : { "title" : _("Block Device %d") },
    ".hardware.storage.disks:*.signature"              : { "title" : _("Disk ID") },
    ".hardware.storage.disks:*.vendor"                 : { "title" : _("Vendor") },
    ".hardware.storage.disks:*.local"                  : { "title" : _("Local") },
    ".hardware.storage.disks:*.bus"                    : { "title" : _("Bus") },
    ".hardware.storage.disks:*.product"                : { "title" : _("Product") },
    ".hardware.storage.disks:*.fsnode"                 : { "title" : _("Filesystem Node") },
    ".hardware.storage.disks:*.serial"                 : { "title" : _("Serial Number") },
    ".hardware.storage.disks:*.size"                   : { "title" : _("Size") },
    ".hardware.storage.disks:*.type"                   : { "title" : _("Type") },
    ".hardware.video:"                                 : { "title" : _("Graphic Cards") },
    ".hardware.video:*."                               : { "title" : _("Graphic Card %d") },
    ".hardware.video:*.name"                           : { "title" : _("Graphic Card Name"), "short" : _("Card Name") },
    ".hardware.video:*.subsystem"                      : { "title" : _("Vendor and Device ID"), "short" : _("Vendor") },
    ".hardware.video:*.driver"                         : { "title" : _("Driver"), "short" : _("Driver") },
    ".hardware.video:*.driver_date"                    : { "title" : _("Driver Date"), "short" : _("Driver Date") },
    ".hardware.video:*.driver_version"                 : { "title" : _("Driver Version"), "short" : _("Driver Version") },

    ".software."                                       : { "title" : _("Software"), "icon" : "software" },
    ".software.os."                                    : { "title" : _("Operating System") },
    ".software.os.name"                                : { "title" : _("Name"), "short" : _("Operating System") },
    ".software.os.version"                             : { "title" : _("Version"), },
    ".software.os.vendor"                              : { "title" : _("Vendor"), },
    ".software.os.type"                                : { "title" : _("Type"), }, # e.g. "linux"
    ".software.os.install_date"                        : { "title" : _("Install Date"), "paint" : "date" },
    ".software.os.kernel_version"                      : { "title" : _("Kernel Version"), "short" : _("Kernel") },
    ".software.os.arch"                                : { "title" : _("Kernel Architecture"), "short" : _("Architecture") },
    ".software.os.service_pack"                        : { "title" : _("Service Pack"), "short" : _("Service Pack") },
    ".software.os.service_packs:"                      : { "title" : _("Service Packs"), "render" : render_inv_dicttable,
                                                            "keyorder" : [ "name" ] },
    ".software.packages:"                              : { "title" : _("Packages"), "icon" : "packages", "render": render_inv_dicttable,
                                                           "keyorder" : [ "name", "version", "arch", "package_type", "summary"] },
    ".software.packages:*.name"                        : { "title" : _("Name"), },
    ".software.packages:*.arch"                        : { "title" : _("Architecture"), },
    ".software.packages:*.package_type"                : { "title" : _("Type"), },
    ".software.packages:*.summary"                     : { "title" : _("Description"), },
    ".software.packages:*.version"                     : { "title" : _("Version"), },
    ".software.packages:*.vendor"                      : { "title" : _("Publisher"), },
    ".software.packages:*.package_version"             : { "title" : _("Package Version"), },
    ".software.packages:*.install_date"                : { "title" : _("Install Date"), "paint" : "date"},
    ".software.packages:*.size"                        : { "title" : _("Size"), "paint" : "count" },
    ".software.packages:*.path"                        : { "title" : _("Path"), },
})

# TEST: create painters for node with a display hint
for invpath, hint in inventory_displayhints.items():
    if "*" not in invpath:
        datatype = hint.get("paint", "str")
        long_title = inv_titleinfo_long(invpath, None)
        declare_inv_column(invpath, datatype, long_title, hint.get("short", long_title))

# View for Inventory tree of one host
multisite_builtin_views["inv_host"] = {
    # General options
    'datasource'                   : 'hosts',
    'topic'                        : _('Inventory'),
    'title'                        : _('Inventory of host'),
    'linktitle'                    : _('Inventory'),
    'description'                  : _('The complete hardware- and software inventory of a host'),
    'icon'                         : 'inventory',
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


def inv_software_table(columns, add_headers, only_sites, limit, filters):
    return inv_multisite_table("invswpacs", columns, add_headers, only_sites, limit, filters)

def inv_multisite_table(dsname, columns, add_headers, only_sites, limit, filters):
    # Create livestatus filter for filtering out hosts
    filter_code = ""
    for filt in filters:
        header = filt.filter(dsname)
        if not header.startswith("Sites:"):
            filter_code += header
    host_columns = list(set([ "host_name" ] + filter(lambda c: c.startswith("host_"), columns)))

    html.live.set_only_sites(only_sites)
    html.live.set_prepend_site(True)

    query = "GET hosts\n"
    query += "Columns: " + (" ".join(host_columns)) + "\n"
    query += filter_code

    if config.debug_livestatus_queries \
            and html.output_format == "html" and 'W' in html.display_options:
        html.write('<div class="livestatus message" onmouseover="this.style.display=\'none\';">'
                           '<tt>%s</tt></div>\n' % (query.replace('\n', '<br>\n')))

    html.live.set_only_sites(only_sites)
    html.live.set_prepend_site(True)

    data = html.live.query(query)

    html.live.set_prepend_site(False)
    html.live.set_only_sites(None)

    headers = [ "site" ] + host_columns

    # Now create big table of all software packages / inventory histories of these hosts

    rows = []
    hostnames = [ row[1] for row in data ]
    for row in data:
        site     = row[0]
        hostname = row[1]
        hostrow = dict(zip(headers, row))
        if dsname == "invswpacs":
            subrows = create_swpac_rows(hostname)
        else:
            subrows = create_hist_rows(hostname, columns)

        for subrow in subrows:
            subrow.update(hostrow)
            rows.append(subrow)
    return rows


def create_swpac_rows(hostname):
    tree     = inventory.host(hostname)
    packages = inventory.get(tree, ".software.packages:")
    for package in packages:
        newrow = {}
        for key, value in package.items():
            newrow["invswpac_" + key] = value
        yield newrow

def declare_swpacs_columns(name, title, sortfunc):
    column = "invswpac_" + name
    multisite_painters[column] = {
        "title"   : _("Package") + " " + title,
        "short"   : title,
        "columns" : [ "invswpac_name" ],
        "paint"   : lambda row: ("", str(row.get(column))),
        "sorter"  : column,
    }
    multisite_sorters[column] = {
        "title"    : _("Inventory") + ": " + title,
        "columns"  : [],
        "cmp"      : lambda a, b: sortfunc(a.get(column), b.get(column))
    }

    if sortfunc == visuals.cmp_version:
        visuals.declare_filter(801, visuals.FilterSWPacsVersion(name, _("Software Package") + ": " + title))
    else:
        visuals.declare_filter(800, visuals.FilterSWPacsText(name, _("Software Package") + ": " + title))


for name, title, sortfunc in [
    ( "name",            _("Name"),             cmp ),
    ( "summary",         _("Summary"),          cmp ),
    ( "arch",            _("CPU Architecture"), cmp ),
    ( "package_type",    _("Type"),             cmp ),
    ( "package_version", _("Package Version"),  visuals.cmp_version ),
    ( "version",         _("Version"),          visuals.cmp_version ),
    ( "install_date",    _("Install Date"),     cmp ),
    ]:
    declare_swpacs_columns(name, title, sortfunc)


multisite_datasources["invswpacs"] = {
    "title"        : _("Inventory: Software Packages"),
    "table"        : inv_software_table,
    "infos"        : [ "host", "invswpac" ],
    "keys"         : [],
    "idkeys"       : [],
}

# View for searching for a certain software
multisite_builtin_views["inv_swpacs"] = {
    # General options
    'datasource'                   : 'invswpacs',
    'topic'                        : _('Inventory'),
    'title'                        : _('Software Package Search'),
    'description'                  : _('Search for software packages installed on hosts'),
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
    'mustsearch'                   : True,
    'mobile'                       : False,

    # Columns
    'group_painters'               : [],
    'painters'                     : [
         ('host',                  'inv_host', ''),
         ('invswpac_name',         '',         ''),
         ('invswpac_summary',      '',         ''),
         ('invswpac_version',      '',         ''),
         ('invswpac_package_version', '',         ''),
         ('invswpac_arch',         '',         ''),
         ('invswpac_package_type', '',         ''),
    ],

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
        'host_favorites',
        'invswpac',
        'invswpac_name',
        'invswpac_summary',
        'invswpac_arch',
        'invswpac_package_type',
        'invswpac_version',
        'invswpac_package_version',
     ],
    'hard_filters'                 : [
        'has_inv'
    ],
    'hard_filtervars'              : [
        ('is_has_inv', '1' ),
    ],
    'hide_filters'                 : [],
    'sorters'                      : [],
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
    return inv_multisite_table("invhist", columns, add_headers, only_sites, limit, filters)

def create_hist_rows(hostname, columns):
    hist_tree = None
    # Iterate over all known historic inventory states - from new to old
    for timestamp in inventory.get_host_history(hostname)[::-1]:
        old_hist_tree = hist_tree
        hist_tree = inventory.load_historic_host(hostname, timestamp)
        removed, new, changed, delta_tree = inventory.compare_trees(old_hist_tree, hist_tree)
        newrow = {
            "invhist_time"    : timestamp,
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
    "idkeys"       : [ "host_name", "invhist_date" ],
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
    "paint"    : lambda row: paint_inv_tree(row, column="invhist_delta"),
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


# sorteres
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

