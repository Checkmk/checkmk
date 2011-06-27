#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

import wato


class FilterWatoFile(Filter):
    def __init__(self):
        Filter.__init__(self, "filename", "WATO Folder/File", "host", ["filename"], [])
        self.tree = wato.api.get_folder_tree()
        self.path_to_tree = {} # keep mapping from string-paths to folders/files
        self.selection = self.folder_selection(self.tree, "", 0)

    def display(self):
        html.select(self.name, [("", "")] + self.selection)

    def filter(self, infoname):
        current = html.var(self.name)
        if current and current in self.path_to_tree:
            return "Filter: host_filename ~ ^%s\n" % current.replace("\n", "") # prevent insertions attack
        else:
            return ""

    def folder_selection(self, folder, prefix, depth):
        my_path = prefix + folder[".name"]
        if not my_path.endswith(".mk"):
            my_path += "/"

        if depth:
            title_prefix = "&nbsp;&nbsp;&nbsp;" * depth + "` " + "- " * depth
        else:
            title_prefix = ""
        self.path_to_tree[my_path] = folder["title"]
        sel = [ (my_path , title_prefix + folder["title"]) ]
        sel += self.sublist(folder.get(".files", {}), my_path, depth)
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
        current = html.var(self.name)
        if current and current != "/":
            return self.path_to_tree.get(current) 



declare_filter(10, FilterWatoFile())
ubiquitary_filters.append("filename") # show in all views
