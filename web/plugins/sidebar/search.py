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

def render_searchform():
    html.write('<div id="mk_side_search" class="content_center" onclick="mkSearchClose();">\n')
    html.write('<input id="mk_side_search_field" type="text" name="search" autocomplete="off" />\n')
    html.icon_button("#", _("Search"), "quicksearch", onclick="mkSearchButton();")
    html.write('</div>\n<div id=mk_side_clear></div>\n')
    html.write("<script type='text/javascript' src='js/search.js'></script>\n")

sidebar_snapins["search"] = {
    "title":       _("Quicksearch"),
    "description": _("Interactive search field for direct access to hosts and services"),
    "render":      render_searchform,
    "restart":     False,
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

#   .--Search Plugins------------------------------------------------------.
#   |  ____                      _       ____  _             _             |
#   | / ___|  ___  __ _ _ __ ___| |__   |  _ \| |_   _  __ _(_)_ __  ___   |
#   | \___ \ / _ \/ _` | '__/ __| '_ \  | |_) | | | | |/ _` | | '_ \/ __|  |
#   |  ___) |  __/ (_| | | | (__| | | | |  __/| | |_| | (_| | | | | \__ \  |
#   | |____/ \___|\__,_|_|  \___|_| |_| |_|   |_|\__,_|\__, |_|_| |_|___/  |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+
#   | Realize the search mechanism to find objects via livestatus          |
#   '----------------------------------------------------------------------'

def search_filter_name(q, column = 'name'):
    return 'Filter: %s ~~ %s\n' % (column, q)

search_plugins.append({
    'type'        : 'host',
    'filter_func' : search_filter_name,
})

search_plugins.append({
    'type'        : 'service',
    'filter_func' : lambda q: search_filter_name(q, 'description'),
})

search_plugins.append({
    'type'        : 'hostgroup',
    'filter_func' : search_filter_name,
})

search_plugins.append({
    'type'        : 'servicegroup',
    'filter_func' : search_filter_name,
})

def search_filter_ipaddress(q):
    if is_ipaddress(q):
        return 'Filter: address ~~ %s\n' % q

search_plugins.append({
    'type'        : 'host',
    'filter_func' : search_filter_ipaddress,
})

def search_filter_alias(q):
    return 'Filter: alias ~~ %s\n' % q

search_plugins.append({
    'type'        : 'host',
    'filter_func' : search_filter_alias,
})
