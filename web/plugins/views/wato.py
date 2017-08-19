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

import config
import watolib


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
    try:
        title_path = watolib.get_folder_title_path(wato_path, with_links)
    except MKGeneralException:
        # happens when a path can not be resolved using the local WATO.
        # e.g. when having an independent site with different folder
        # hierarchy added to the GUI.
        # Display the raw path rather than the exception text.
        title_path = wato_path.split("/")
    except Exception, e:
        return "%s" % e

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
