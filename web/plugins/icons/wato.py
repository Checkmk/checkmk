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
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

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
            url += "&mode=edithost"
            help = _("Edit this host")
            icon = "wato"
        return icon, help, url
    else:
        return

def paint_wato(what, row, tags, custom_vars):
    if not wato.may_see_hosts() or html.mobile:
        return

    filename = row["host_filename"]
    if filename.startswith("/wato/") and filename.endswith("hosts.mk"):
        wato_folder = filename[6:-8].rstrip("/")
        if what == "host":
            return wato_link(wato_folder, row["site"], row["host_name"], "edithost")
        elif row["service_description"] in [ "Check_MK inventory", "Check_MK Discovery" ]:
            return wato_link(wato_folder, row["site"], row["host_name"], "inventory")

multisite_icons_and_actions['wato'] = {
    'host_columns' : [ "filename" ],
    'paint'        :  paint_wato,
}
