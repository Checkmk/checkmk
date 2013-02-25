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

# +------------------------------------------------------------------+
# | This file has been contributed and is copyrighted by:            |
# |                                                                  |
# | Lars Michelsen <lm@mathias-kettner.de>            Copyright 2010 |
# +------------------------------------------------------------------+

import views, defaults

def render_nagvis_maps():
    refresh_url = "%snagvis/server/core/ajax_handler.php?mod=Multisite&act=getMaps" % (defaults.url_prefix)
    return refresh_url

sidebar_snapins["nagvis_maps"] = {
    "title":       _("NagVis Maps"),
    "description": _("List of available NagVis maps. This only works with NagVis 1.5 and above. " \
                   "At the moment it is neccessarry to authenticate with NagVis first by opening " \
                   "a NagVis map in the browser. After this the maplist should be filled."),
    "render":      render_nagvis_maps,
    "allowed":     [ "user", "admin", "guest" ],
    "refresh":     True,
    "styles":      ""
}
