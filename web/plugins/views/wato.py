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

import config, wato


class FilterWatoFile(Filter):
    def __init__(self):
        Filter.__init__(self, "wato_folder", _("WATO Folder"), "host", ["filename"], [])
        self.last_wato_data_update = None

    def available(self):
        return config.wato_enabled and wato.have_folders()

    def load_wato_data(self):
        self.tree = wato.api.get_folder_tree()
        self.path_to_tree = {} # will be filled by self.folder_selection
        self.selection = self.folder_selection(self.tree, "", 0)
        self.last_wato_data_update = time.time()

    def check_wato_data_update(self):
        if not self.last_wato_data_update or time.time() - self.last_wato_data_update > 5:
            self.load_wato_data()

    def display(self):
        self.check_wato_data_update()
        html.select(self.name, [("", "")] + self.selection)

    def filter(self, infoname):
        self.check_wato_data_update()
        current = html.var(self.name)
        if current:
            return "Filter: host_filename ~ ^/wato/%s/\n" % current.replace("\n", "") # prevent insertions attack
        else:
            return ""

    # Construct pair-list of ( folder-path, title ) to be used
    # by the HTML selection box. This also updates self._tree,
    # a dictionary from the path to the title.
    def folder_selection(self, folder, prefix, depth):
        my_path = folder[".path"]
        if depth:
            title_prefix = "&nbsp;&nbsp;&nbsp;" * depth + "` " + "- " * depth
        else:
            title_prefix = ""
        self.path_to_tree[my_path] = folder["title"]
        sel = [ (my_path , title_prefix + folder["title"]) ]
        sel += self.sublist(folder.get(".folders", {}), my_path, depth)
        return sel

    def sublist(self, elements, my_path, depth):
        vs = elements.values()
        vs.sort(lambda a, b: cmp(a["title"].lower(), b["title"].lower()))
        sel = []
        for e in vs:
            sel += self.folder_selection(e, my_path, depth + 1)
        return sel

    def heading_info(self, info):
        # FIXME: There is a problem with caching data and changing titles of WATO files
        # Everything is changed correctly but the filter object is stored in the
        # global multisite_filters var and self.path_to_tree is not refreshed when
        # rendering this title. Thus the threads might have old information about the
        # file titles and so on.
        # The call below needs to use some sort of indicator wether the cache needs
        # to be renewed or not.
        self.check_wato_data_update()
        current = html.var(self.name)
        if current and current != "/":
            return self.path_to_tree.get(current)

declare_filter(10, FilterWatoFile())
if "wato_folder" not in ubiquitary_filters:
    ubiquitary_filters.append("wato_folder") # show in all views

multisite_painters["host_filename"] = {
    "title"   : _("Check_MK config filename"),
    "short"   : _("Filename"),
    "columns" : ["host_filename"],
    "paint"   : lambda row: ("tt", row["host_filename"]),
}

def get_wato_folder(row, how, with_links = True):
    filename = row["host_filename"]
    if not filename.startswith("/wato/") or not filename.endswith("/hosts.mk"):
        return ""
    wato_path = filename[6:-9]
    title_path = wato.api.get_folder_title_path(wato_path, with_links)
    if how == "plain":
        return title_path[-1]
    elif how == "abs":
        return " / ".join(title_path)
    else:
        # We assume that only hosts are show, that are below the
        # current WATO path. If not then better output absolute
        # path then wrong path.
        current_path = html.var("wato_folder")
        if not current_path or not wato_path.startswith(current_path):
            return " / ".join(title_path)

        depth = current_path.count('/') + 1
        return " / ".join(title_path[depth:])

def paint_wato_folder(row, how):
    return "", get_wato_folder(row, how)


multisite_painters["wato_folder_abs"] = {
    "title"   : _("WATO folder - complete path"),
    "short"   : _("WATO folder"),
    "columns" : ["host_filename"],
    "paint"   : lambda row: paint_wato_folder(row, "abs"),
    "sorter"  : 'wato_folder_abs',
}

multisite_painters["wato_folder_rel"] = {
    "title"   : _("WATO folder - relative path"),
    "short"   : _("WATO folder"),
    "columns" : ["host_filename"],
    "paint"   : lambda row: paint_wato_folder(row, "rel"),
    "sorter"  : 'wato_folder_rel',
}

multisite_painters["wato_folder_plain"] = {
    "title"   : _("WATO folder - just folder name"),
    "short"   : _("WATO folder"),
    "columns" : ["host_filename"],
    "paint"   : lambda row: paint_wato_folder(row, "plain"),
    "sorter"  : 'wato_folder_plain',
}

def cmp_wato_folder(r1, r2, how):
    return cmp(get_wato_folder(r1, how, False), get_wato_folder(r2, how, False))

multisite_sorters["wato_folder_abs"] = {
    "title"   : _("WATO folder - complete path"),
    "columns" : [ "host_filename" ],
    "cmp"     : lambda r1, r2: cmp_wato_folder(r1, r2, 'abs'),
}

multisite_sorters["wato_folder_rel"] = {
    "title"   : _("WATO folder - relative path"),
    "columns" : [ "host_filename" ],
    "cmp"     : lambda r1, r2: cmp_wato_folder(r1, r2, 'rel'),
}

multisite_sorters["wato_folder_plain"] = {
    "title"   : _("WATO folder - just folder name"),
    "columns" : [ "host_filename" ],
    "cmp"     : lambda r1, r2: cmp_wato_folder(r1, r2, 'plain'),
}
