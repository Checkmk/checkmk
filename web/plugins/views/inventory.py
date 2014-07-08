#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
    elif type(invdata) in ( list, dict ):
        return paint_inv_tree(row, invpath)
    else:
        return "number", str(invdata)

def cmp_inventory_node(a, b, invpath):
    val_a = inventory.get(a["host_inventory"], invpath)
    val_b = inventory.get(b["host_inventory"], invpath)
    return cmp(a, b)

class FilterInvText(Filter):
    def __init__(self, name, invpath, title):
        self._invpath = invpath
        Filter.__init__(self, name, title, "host", [name], [])

    def need_inventory(self):
        return True

    def display(self):
        htmlvar = self.htmlvars[0]
        current_value = html.var(htmlvar, "")
        html.text_input(htmlvar, current_value)

    def filter_table(self, rows):
        htmlvar = self.htmlvars[0]
        filtertext = html.var(htmlvar, "").strip().lower()
        if not filtertext:
            return rows

        regex = re.compile(filtertext, re.IGNORECASE)

        newrows = []
        for row in rows:
            invdata = inventory.get(row["host_inventory"], self._invpath)
            if invdata == None:
                invdata = ""
            if regex.search(invdata):
                newrows.append(row)
        return newrows

class FilterInvFloat(Filter):
    def __init__(self, name, invpath, title, unit="", scale=1.0):
        self._invpath = invpath
        self._unit = unit
        self._scale = scale
        Filter.__init__(self, name, title, "host", [name + "_from", name + "_to"], [])

    def need_inventory(self):
        return True

    def display(self):
        html.write(_("From: "))
        htmlvar = self.htmlvars[0]
        current_value = html.var(htmlvar, "")
        html.number_input(htmlvar, current_value)
        if self._unit:
            html.write(self._unit)

        html.write("&nbsp;&nbsp;" + _("To: " ))
        htmlvar = self.htmlvars[1]
        current_value = html.var(htmlvar, "")
        html.number_input(htmlvar, current_value)
        if self._unit:
            html.write(self._unit)

    def filter_table(self, rows):
        fromvar = self.htmlvars[0]
        fromtext = html.var(fromvar)
        lower = None
        if fromtext:
            try:
                lower = float(fromtext) * self._scale
            except:
                pass

        tovar = self.htmlvars[1]
        totext = html.var(tovar)
        upper = None
        if totext:
            try:
                upper = float(totext) * self._scale
            except:
                pass

        if lower == None and upper == None:
            return rows

        newrows = []
        for row in rows:
            invdata = inventory.get(row["host_inventory"], self._invpath)
            if lower != None and invdata < lower:
                continue
            if upper != None and invdata > upper:
                continue
            newrows.append(row)
        return newrows

class FilterHasInventory(FilterTristate):
    def __init__(self):
        FilterTristate.__init__(self, "has_inv", _("Has Inventory Data"), "host", "host_inventory")

    def filter(self, infoname):
        return "" # No Livestatus filtering right now

    def filter_table(self, rows):
        return [ row for row in rows if row["host_inventory"] ]

class FilterInvHasSoftwarePackage(Filter):
    def __init__(self):
        self._varprefix = "invswpac_host_"
        Filter.__init__(self, "invswpac", _("Host has software package"), "host",
                        [ self._varprefix + "name", self._varprefix + "version_from",
                          self._varprefix + "version_to", self._varprefix + "negate"], [])

    def double_height(self):
        return True

    def need_inventory(self):
        return True

    def display(self):
        html.text_input(self._varprefix + "name")
        html.write("<br>")
        html.begin_radio_group(horizontal=True)
        html.radiobutton(self._varprefix + "match", "exact", True, label=_("exact match"))
        html.radiobutton(self._varprefix + "match", "regex", False, label=_("regular expression, substring match"))
        html.end_radio_group()
        html.write("<br>")
        html.write(_("Min.&nbsp;Version:"))
        html.text_input(self._varprefix + "version_from", size = 9)
        html.write(" &nbsp; ")
        html.write(_("Max.&nbsp;Vers.:"))
        html.text_input(self._varprefix + "version_to", size = 9)
        html.write("<br>")
        html.checkbox(self._varprefix + "negate", False, label=_("Negate: find hosts <b>not</b> having this package"))

    def filter_table(self, rows):
        name = html.var_utf8(self._varprefix + "name")
        if not name:
            return rows

        from_version = html.var(self._varprefix + "from_version")
        to_version   = html.var(self._varprefix + "to_version")
        negate       = html.get_checkbox(self._varprefix + "negate")
        match        = html.var(self._varprefix + "match")
        if match == "regex":
            name = re.compile(name)

        new_rows = []
        for row in rows:
            packages = inventory.get(row["host_inventory"], ".software.packages:")
            is_in = self.find_package(packages, name, from_version, to_version)
            if is_in != negate:
                new_rows.append(row)
        return new_rows

    def find_package(self, packages, name, from_version, to_version):
        for package in packages:
            if type(name) == unicode:
                if package["name"] != name:
                    continue
            else:
                if not name.search(package["name"]):
                    continue
            if not from_version and not to_version:
                return True # version not relevant
            version = package["version"]
            if from_version == to_version and from_version != version:
                continue
            if from_version and self.version_is_lower(version, from_version):
                continue
            if to_version and self.version_is_higher(version, to_version):
                continue
        return False

    def version_is_lower(self, a, b):
        return a != b and not self.version_is_higher(a, b)

    def version_is_higher(self, a, b):
        return cmp_version(a, b) == 1


# Try to magically compare two software versions.
# Currently we only assume the format A.B.C.D....
# When we suceed converting A to a number, then we
# compare by integer, otherwise by text.
def try_int(x):
    try:
        return int(x)
    except:
        return x

def cmp_version(a, b):
    if a == None or b == None:
        return cmp(a, b)
    aa = map(try_int, a.split("."))
    bb = map(try_int, b.split("."))
    return cmp(aa, bb)



inv_filter_info = {
    "bytes"         : { "unit" : _("MB"),    "scale" : 1024*1024 },
    "bytes_rounded" : { "unit" : _("MB"),    "scale" : 1024*1024 },
    "hz"            : { "unit" : _("MHz"),   "scale" : 1000000 },
    "volt"          : { "unit" : _("Volt") },
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
            declare_filter(800, FilterInvText(name, invpath, title))
        else:
            filter_info = inv_filter_info.get(datatype, {})
            declare_filter(800, FilterInvFloat(name, invpath, title,
               unit = filter_info.get("unit"),
               scale = filter_info.get("scale", 1.0)))


# Tree painter
def paint_inv_tree(row, invpath = "."):
    hostname = row["host_name"]
    tree = row["host_inventory"]
    node = inventory.get(tree, invpath)
    html.plug()
    render_inv_subtree_container(hostname, invpath, node)
    code = html.drain()
    html.unplug()
    return "invtree", code

def render_inv_subtree(hostname, invpath, node):
    if type(node) in (dict, list):
        render_inv_subtree_foldable(hostname, invpath, node)
    else:
        render_inv_subtree_leaf(hostname, invpath, node)

def render_inv_subtree_foldable(hostname, invpath, node):
    if node: # omit empty nodes completely
        icon, title = inv_titleinfo(invpath, node)

        if "%d" in title: # Replace with list index
            list_index = int(invpath.split(":")[-1].rstrip(".")) + 1
            title = title % list_index

        fetch_url = html.makeuri_contextless([("host", hostname), ("path", invpath)], "ajax_inv_render_tree.py")
        if html.begin_foldable_container("inv_" + hostname, invpath, False, title, icon=icon, fetch_url=fetch_url):
            # Render only if it is open. We'll get the stuff via ajax later if it's closed
            render_inv_subtree_container(hostname, invpath, node)
        html.end_foldable_container()

def render_inv_subtree_container(hostname, invpath, node):
    hint = inv_display_hint(invpath)
    if "render" in hint:
        hint["render"](hostname, invpath, node)
    elif type(node) == dict:
        render_inv_subtree_dict(hostname, invpath, node)
    else:
        render_inv_subtree_list(hostname, invpath, node)

def render_inv_subtree_dict(hostname, invpath, node):
    items = node.items()
    items.sort()

    leaf_nodes = []
    for key, value in items:
        if type(value) not in (list, dict):
            invpath_sub = invpath + key
            icon, title = inv_titleinfo(invpath_sub, value)
            leaf_nodes.append((title, invpath_sub, value))

    if leaf_nodes:
        leaf_nodes.sort()
        html.write("<table>")
        for title, invpath_sub, value in leaf_nodes:
            html.write("<tr><th title='%s'>%s</th><td>" % (invpath_sub, title))
            render_inv_subtree(hostname, invpath_sub, value)
            html.write("</td></tr>")
        html.write("</table>")

    non_leaf_nodes = [ item for item in items if type(item[1]) in (list, dict) ]
    non_leaf_nodes.sort()
    for key, value in non_leaf_nodes:
        invpath_sub = invpath + key
        if type(value) == dict:
            invpath_sub += "."
        elif type(value) == list:
            invpath_sub += ":"
        render_inv_subtree_foldable(hostname, invpath_sub, value)

def render_inv_subtree_list(hostname, invpath, node):
    if not node:
        return
    for nr, value in enumerate(node):
        invpath_sub = invpath + str(nr)
        if type(value) == dict:
            invpath_sub += "."
        elif type(value) == list:
            invpath_sub += ":"
        render_inv_subtree(hostname, invpath_sub, value)

def render_inv_subtree_leaf(hostname, invpath, node):
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
    html.write("<br>")


def render_inv_dicttable(hostname, invpath, node):
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

    # We cannot use table here, since html.plug does not work recursively
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
            elif type(value) == list:
                invpath_sub += ":"
            html.write('<td>')
            render_inv_subtree(hostname, invpath_sub, value)
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

inventory_displayhints.update({
    "."                                                : { "title" : _("Inventory") },
    ".hardware."                                       : { "title" : _("Hardware"), "icon" : "hardware", },
    ".hardware.bios."                                  : { "title" : _("BIOS"), },
    ".hardware.bios.vendor"                            : { "title" : _("Vendor"), },
    ".hardware.chassis."                               : { "title" : _("Chassis"), },
    ".hardware.cpu."                                   : { "title" : _("Processor"), },
    ".hardware.cpu.model"                              : { "title" : _("Model"), "short" : _("CPU Model"), },
    ".hardware.cpu.cache_size"                         : { "title" : _("Cache Size"),                     "paint" : "bytes" },
    ".hardware.cpu.max_speed"                          : { "title" : _("Maximum Speed"),                  "paint" : "hz" },
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
    ".software.os.kernel_version"                      : { "title" : _("Kernel Version"), "short" : _("Kernel") },
    ".software.os.arch"                                : { "title" : _("Kernel Architecture"), "short" : _("Architecture") },
    ".software.os.service_pack"                        : { "title" : _("Service Pack"), "short" : _("Service Pack") },
    ".software.packages:"                              : { "title" : _("Packages"), "icon" : "packages", "render": render_inv_dicttable,
                                                           "keyorder" : [ "name", "version", "arch", "package_type", "summary"] },
    ".software.packages:*.name"                        : { "title" : _("Name"), },
    ".software.packages:*.arch"                        : { "title" : _("Architecture"), },
    ".software.packages:*.package_type"                : { "title" : _("Type"), },
    ".software.packages:*.summary"                     : { "title" : _("Description"), },
    ".software.packages:*.version"                     : { "title" : _("Version"), },
    ".software.packages:*.vendor"                      : { "title" : _("Publisher"), },
    ".software.packages:*.package_version"             : { "title" : _("Package Version"), },
    ".software.packages:*.install_date"                : { "title" : _("Install Date"), },
    ".software.packages:*.size"                        : { "title" : _("Size"), "paint" : "count" },
    ".software.packages:*.path"                        : { "title" : _("Path"), },
})

# TEST: create painters for node with a display hint
for invpath, hint in inventory_displayhints.items():
    if "*" not in invpath:
        datatype = hint.get("paint", "str")
        long_title = inv_titleinfo_long(invpath, None)
        declare_inv_column(invpath, datatype, long_title, hint.get("short", long_title))

declare_filter(801, FilterHasInventory())
declare_filter(801, FilterInvHasSoftwarePackage())

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
    'hide_filters'                 : ['host', 'site'],
    'show_filters'                 : [
         'inv_hardware_cpu_cpus',
         'inv_hardware_cpu_cores',
         'inv_hardware_cpu_max_speed',
     ],
    'sorters'                      : [],
}


def inv_software_table(columns, add_headers, only_sites, limit, filters):
    # Create livestatus filter for filtering out hosts
    filter_code = ""
    for filt in filters:
        header = filt.filter("invswpacs")
        if not header.startswith("Sites:"):
            filter_code += header
    host_columns = [ "host_name" ] + filter(lambda c: c.startswith("host_"), columns)

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

    # Now create big table of all software packages of these hosts
    rows = []
    hostnames = [ row[1] for row in data ]
    for row in data:
        site     = row[0]
        hostname = row[1]
        tree     = inventory.host(hostname)
        hostrow = dict(zip(headers, row))
        packages = inventory.get(tree, ".software.packages:")
        for package in packages:
            newrow = {}
            for key, value in package.items():
                newrow["invswpac_" + key] = value
            newrow.update(hostrow)
            rows.append(newrow)

    return rows

class FilterSWPacsText(Filter):
    def __init__(self, name, title):
        varname = "invswpac_" + name
        Filter.__init__(self, varname, title, "invswpacs", [varname], [])

    def display(self):
        htmlvar = self.htmlvars[0]
        current_value = html.var(htmlvar, "")
        html.text_input(htmlvar, current_value)

    def filter_table(self, rows):
        htmlvar = self.htmlvars[0]
        filtertext = html.var(htmlvar, "").strip().lower()
        if not filtertext:
            return rows

        regex = re.compile(filtertext, re.IGNORECASE)

        newrows = []
        for row in rows:
            if regex.search(row.get(htmlvar, "")):
                newrows.append(row)
        return newrows

class FilterSWPacsVersion(Filter):
    def __init__(self, name, title):
        varname = "invswpac_" + name
        Filter.__init__(self, varname, title, "invswpacs", [varname + "_from", varname + "_to"], [])

    def display(self):
        htmlvar = self.htmlvars[0]
        html.write(_("Min.&nbsp;Version:"))
        html.text_input(self.htmlvars[0], size = 9)
        html.write(" &nbsp; ")
        html.write(_("Max.&nbsp;Version:"))
        html.text_input(self.htmlvars[1], size = 9)

    def filter_table(self, rows):
        from_version = html.var(self.htmlvars[0])
        to_version   = html.var(self.htmlvars[1])
        if not from_version and not to_version:
            return rows # Filter not used

        new_rows = []
        for row in rows:
            version = row.get(self.name, "")
            if from_version and cmp_version(version, from_version) == -1:
                continue
            if to_version and cmp_version(version, to_version) == 1:
                continue
            new_rows.append(row)

        return new_rows

def declare_swpacs_columns(name, title, sortfunc):
    column = "invswpac_" + name
    multisite_painters[column] = {
        "title"   : _("Package") + " " + title,
        "short"   : title,
        "columns" : [ "invswpac_name" ],
        "paint"   : lambda row: ("", row.get(column)),
        "sorter"  : column,
    }
    multisite_sorters[column] = {
        "title"    : _("Inventory") + ": " + title,
        "columns"  : [],
        "cmp"      : lambda a, b: sortfunc(a.get(column), b.get(column))
    }

    if sortfunc == cmp_version:
        declare_filter(801, FilterSWPacsVersion(name, _("Software Package") + ": " + title))
    else:
        declare_filter(800, FilterSWPacsText(name, _("Software Package") + ": " + title))


for name, title, sortfunc in [
    ( "name",            _("Name"),             cmp ),
    ( "summary",         _("Summary"),          cmp ),
    ( "arch",            _("CPU Architecture"), cmp ),
    ( "package_type",    _("Type"),             cmp ),
    ( "package_version", _("Package Version"),  cmp_version ),
    ( "version",         _("Version"),          cmp_version ),
    ( "install_date",    _("Install Date"),     cmp ),
    ]:
    declare_swpacs_columns(name, title, sortfunc)




multisite_datasources["invswpacs"] = {
    "title"       : _("Inventory: Software Packages"),
    "table"       : inv_software_table,
    "infos"       : [ "host", "invswpac" ],
    "keys"        : [],
    "idkeys"      : [],
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
