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

import wato

def wato_link(folder, site, hostname, where):
    if not config.wato_enabled:
        return

    if 'X' in html.display_options:
        url = "wato.py?folder=%s&host=%s" % \
           (html.urlencode(folder), html.urlencode(hostname))
        if where == "inventory":
            url += "&mode=inventory"
            help = _("Edit services")
            icon = "services"
        else:
            url += "&mode=edit_host"
            help = _("Edit this host")
            icon = "wato"
        return icon, help, url
    else:
        return


def wato_folder_from_filename(filename):
    if filename.startswith("/wato/") and filename.endswith("hosts.mk"):
        return filename[6:-8].rstrip("/")


def paint_wato(what, row, tags, custom_vars):
    if not wato.may_see_hosts() or html.mobile:
        return

    wato_folder = wato_folder_from_filename(row["host_filename"])
    if wato_folder != None:
        if what == "host":
            return wato_link(wato_folder, row["site"], row["host_name"], "edithost")
        elif row["service_description"] in [ "Check_MK inventory", "Check_MK Discovery" ]:
            return wato_link(wato_folder, row["site"], row["host_name"], "inventory")


multisite_icons_and_actions['wato'] = {
    'host_columns' : [ "filename" ],
    'paint'        :  paint_wato,
}

#.
#   .--Agent-Output--------------------------------------------------------.
#   |     _                    _         ___        _               _      |
#   |    / \   __ _  ___ _ __ | |_      / _ \ _   _| |_ _ __  _   _| |_    |
#   |   / _ \ / _` |/ _ \ '_ \| __|____| | | | | | | __| '_ \| | | | __|   |
#   |  / ___ \ (_| |  __/ | | | ||_____| |_| | |_| | |_| |_) | |_| | |_    |
#   | /_/   \_\__, |\___|_| |_|\__|     \___/ \__,_|\__| .__/ \__,_|\__|   |
#   |         |___/                                    |_|                 |
#   +----------------------------------------------------------------------+
#   | Action for downloading the current agent output                      |
#   '----------------------------------------------------------------------'

def paint_download_agent_output(what, row, tags, host_custom_vars, ty):
    if (what == "host" or (what == "service" and row["service_description"] == "Check_MK")) \
       and config.may("wato.download_agent_output") \
       and not row["host_check_type"] == 2: # Not for shadow hosts

        # Not 100% acurate to use the tags here, but this is the best we can do
        # with the available information.
        # Render "download agent output" for non agent hosts, because there might
        # be piggyback data available which should be downloadable.
        if ty == "walk" and "snmp" not in tags:
            return
        elif ty == "agent" and "snmp" in tags and "tcp" not in tags:
            return

        params = [("host",   row["host_name"]),
                  ("folder", wato_folder_from_filename(row["host_filename"])),
                  ("type",   ty)]

        if ty == "agent":
            title = _("Download agent output")
        else:
            title = _("Download SNMP walk")

        url = html.makeuri_contextless(params, filename="download_agent_output.py")
        return "agent_output", title, url


multisite_icons_and_actions['download_agent_output'] = {
    'host_columns'    : [ "filename", "check_type" ],
    'paint'           : lambda what, row, tags, host_custom_vars: paint_download_agent_output(what, row, tags, host_custom_vars, ty="agent"),
    'toplevel'        : False,
    'sort_index'      : 50,
}

multisite_icons_and_actions['download_snmp_walk'] = {
    'host_columns'    : [ "filename" ],
    'paint'           : lambda what, row, tags, host_custom_vars: paint_download_agent_output(what, row, tags, host_custom_vars, ty="walk"),
    'toplevel'        : False,
    'sort_index'      : 50,
}
