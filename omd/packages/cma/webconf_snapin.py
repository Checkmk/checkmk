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

def render_webconf():
    # Our version of iconlink -> the images are located elsewhere
    def iconlink(text, url, icon):
        html.open_a(class_=["iconlink", "link"], target="main", href=url)
        html.icon(icon="/webconf/images/icon_%s.png" % icon, help=None, cssclass="inline")
        html.write(text)
        html.close_a()
        html.br()

    base_url = "/webconf/"

    iconlink(_("Main Menu"), base_url, "home")

    import imp
    cma_nav = imp.load_source("cma_nav", "/usr/lib/python2.7/cma_nav.py")
    for url, icon, title, descr in cma_nav.modules():
        url = base_url + url
        iconlink(title, url, icon)

sidebar_snapins["webconf"] = {
    "title"         : _("Check_MK Appliance"),
    "description"   : _("Access to the Check_MK Appliance Web Configuration"),
    "render"        : render_webconf,
    "allowed"       : [ "admin" ],
}
