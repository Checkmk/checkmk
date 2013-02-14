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

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

def render_searchform():
    try:
        limit = config.quicksearch_dropdown_limit
    except:
        limit = 80

    html.write('<div id="mk_side_search" class="content_center" onclick="mkSearchClose();">')
    html.write('<input id="mk_side_search_field" type="text" name="search" autocomplete="off" />')
    html.icon_button("#", _("Search"), "quicksearch", onclick="mkSearchButton();")
    html.write('</div><div id=mk_side_clear></div>')
    html.write("<script type='text/javascript' src='js/search.js'></script>\n")
    html.write("<script type='text/javascript'>\n")

    # Store (user) hosts in JS array
    html.live.set_prepend_site(True)

    def sort_data(data):
        sorted_data = set([])
        for entry in data:
            entry = ('', entry[1])
            if entry not in sorted_data:
                sorted_data.add(entry)
        sorted_data = list(sorted_data)
        sorted_data.sort()
        return sorted_data

    try:
        import json
        data = html.live.query("GET hosts\nColumns: name\n")
        html.write("aSearchHosts = %s;\n" % json.dumps(data))
        data = sort_data(html.live.query("GET hostgroups\nColumns: name\n"))
        html.write("aSearchHostgroups = %s;\n" % json.dumps(data))
        data = sort_data(html.live.query("GET servicegroups\nColumns: name\n"))
        html.write("aSearchServicegroups = %s;\n" % json.dumps(data))
        data = sort_data(html.live.query("GET services\nColumns: description\n"))
        html.write("aSearchServices = %s;\n" % json.dumps(data))
    except:
        data = html.live.query("GET hosts\nColumns: name\n", "OutputFormat: json\n")
        html.write("aSearchHosts = %s;\n" % data)
        data = html.live.query("GET hostgroups\nColumns: name\n", "OutputFormat: json\n")
        html.write("aSearchHostgroups = %s;\n" % data)
        data = html.live.query("GET servicegroups\nColumns: name\n", "OutputFormat: json\n")
        html.write("aSearchServicegroups = %s;\n" % data)
        data = html.live.query("GET services\nColumns: description\n", "OutputFormat: json\n")
        html.write("aSearchServices = %s;\n" % data)
    html.write("aSearchLimit = %d;\n" % limit)
    html.live.set_prepend_site(False)

    html.write("</script>\n")

sidebar_snapins["search"] = {
    "title":       _("Quicksearch"),
    "description": _("Interactive search field for direct access to hosts"),
    "render":      render_searchform,
    "restart":     True,
    "allowed":     [ "user", "admin", "guest" ],
    "styles":      """

#mk_side_search {
    width: 232px;
    padding: 0;
}

#mk_side_clear {
    clear: both;
}

#mk_side_search img.iconbutton {
    width: 33px;
    height: 26px;
    margin-top: -25px;
    left: 196px;
    float:right;
    z-index:100;
}

#mk_side_search input {
    margin:  0;
    padding: 0px 5px;
    font-size: 8pt;
    width: 194px;
    height: 25px;
    background-image: url("images/quicksearch_field_bg.png");
    background-repeat: no-repeat;
    -moz-border-radius: 0px;
    border-style: none;
    float: left;
}

#mk_search_results {
    position: relative;
    float:left;
    border: 1px solid white;
    background-color: #DFDFDF;
    color: #000;
    font-size: 80%;
    width: 223px;
}

#mk_search_results a {
    display: block;
    color: #000;
    text-decoration: none;
    text-align: left;
    padding-left: 5px;
    width: 217px;
}

#mk_search_results a:hover, #mk_search_results a.active {
    background-color: #BFBFBF;
}

"""
}
