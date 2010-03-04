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

# +------------------------------------------------------------------+
# | This file has been contributed and is copyrighted by:            |
# |                                                                  |
# | Lars Michelsen <lm@mathias-kettner.de>            Copyright 2010 |
# +------------------------------------------------------------------+

import views, defaults

def render_searchform():
    html.write('<script type="text/javascript" src="%s/search.js"></script>' % defaults.checkmk_web_uri)
    html.write('<div id="mk_side_search">')
    html.write('<input id="mk_side_search_field" type="text" name="search" />')
    html.write('</div>')
    html.write('<script type="text/javascript">')

    # Store (user) hosts in JS array
    data = html.live.query("GET hosts\nColumns: name alias\n")
    html.write('var aSearchHosts = %s;' % data)

    html.write('mkSearchAddField("mk_side_search_field", "main", "%s");</script>' % defaults.checkmk_web_uri)

sidebar_snapins["search"] = {
    "title" : "Quicksearch",
    "render" : render_searchform,
    "allowed" : [ "user", "admin", "guest" ],
}
