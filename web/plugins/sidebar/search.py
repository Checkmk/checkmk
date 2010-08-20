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
    html.write('<div id="mk_side_search" onclick="mkSearchClose();">')
    html.write('<input id="mk_side_search_field" type="text" name="search" />')
    html.write('</div>')
    html.write('<script type="text/javascript" src="search.js"></script>')
    html.write('<script type="text/javascript">')

    # Store (user) hosts in JS array
    html.live.set_prepend_site(True)
    try:
        import json
        data = html.live.query("GET hosts\nColumns: name\n")
        html.write("aSearchHosts = %s;\n" % json.dumps(data))
        data = html.live.query("GET hostgroups\nColumns: name\n")
        html.write("aSearchHostgroups = %s;\n" % json.dumps(data))
        data = html.live.query("GET servicegroups\nColumns: name\n")
        html.write("aSearchServicegroups = %s;\n" % json.dumps(data))
        data = html.live.query("GET services\nColumns: name\n")
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
    html.live.set_prepend_site(False)

    html.write('</script>')

sidebar_snapins["search"] = {
    "title" : "Quicksearch",
    "description" : "Interactive search field for direct access to hosts",
    "author" : "Lars Michelsen",
    "render" : render_searchform,
    "allowed" : [ "user", "admin", "guest" ],
    "styles" : """
div#mk_side_search {
    padding-left: 1px;
    width: %dpx;
}

div#mk_side_search input{
    margin: 0px 1px 0px 0px;
    width: 100%%;
    font-size: 8pt;
}

div#mk_side_search #mk_search_results {
    position: relative;
    border: 1px solid white;
    top: 1px;
    background-color: #DFDFDF;
    color: #000;
    font-size: 80%%;
    width:140px;
}

div#mk_side_search #mk_search_results a {
    display: block;
    color: #000;
    text-decoration: none;
    text-align: left;
    padding-left: 5px;
    width: 135px;
}

div#mk_side_search #mk_search_results a:hover, div#mk_side_search #mk_search_results a.active {
background-color: #BFBFBF;
}

""" % (snapin_width - 1)
}
