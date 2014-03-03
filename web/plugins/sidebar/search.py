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

#.
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

def search_filter_name(used_filters, column = 'name'):
    return 'Filter: %s ~~ %s\n' % (column, used_filters[0][1])

search_plugins.append({
    'id'          : 'hosts',
    "lq_columns"  : ["host_name"],
    'filter_func' : search_filter_name,
})

search_plugins.append({
    'id'          : 'services',
    "lq_columns"  : ["service_description"],
    'filter_func' : lambda q: search_filter_name(q, 'description'),
})

search_plugins.append({
    'id'          : 'hostgroups',
    "lq_columns"  : ["name"],
    'filter_func' : search_filter_name,
})

search_plugins.append({
    'id'          : 'servicegroups',
    "lq_columns"  : ["name"],
    'filter_func' : search_filter_name,
})

def search_filter_ipaddress(used_filters):
    q = used_filters[0][1]
    if is_ipaddress(q):
        return 'Filter: address ~~ %s\n' % q

search_plugins.append({
    'id'             : 'host_address',
    "dftl_url_tmpl"  : "hosts",
    "lq_table"       : "hosts",
    "lq_columns"     : ["host_address"],
    'filter_func'    : search_filter_ipaddress,
    'search_url_tmpl': 'view.py?view_name=searchhost&host_address=%(search)s&filled_in=filter&host_address_prefix=yes',
    'match_url_tmpl' : 'view.py?view_name=searchhost&host_address=%(search)s&filled_in=filter'
})

def search_filter_alias(used_filters):
    return 'Filter: alias ~~ %s\n' % used_filters[0][1]

search_plugins.append({
    'id'              : 'host_alias',
    "dftl_url_tmpl"   : "hosts",
    'lq_table'        : "hosts",
    'qs_show'         : 'host_alias',
    'lq_columns'      : ['host_name', 'host_alias'],
    'filter_func'     : search_filter_alias,
    'search_url_tmpl' : 'view.py?view_name=searchhost&hostalias=%(search)s&filled_in=filter',
    'match_url_tmpl'  : 'view.py?view_name=searchhost&hostalias=%(search)s&filled_in=filter'
})


def search_host_service_filter(filters, host_is_ip = False):
    def get_filters(filter_type):
        result = []
        for entry in filters:
            if entry[0] == filter_type:
                result.append(entry[1])
        return result

    services      = get_filters("services")
    hosts         = get_filters("hosts")
    hostgroups    = get_filters("hostgroups")
    servicegroups = get_filters("servicegroups")

    lq_filter = ""
    group_count = 0
    for filter_name, entries, optr in [ (host_is_ip and "host_address" or "host_name", hosts, "~~"),
                                        ("service_description", services, "~~"),
                                        ("host_groups", hostgroups, ">="),
                                        ("groups", servicegroups, ">=") ]:
        if entries:
            group_count += 1
        for entry in entries:
            lq_filter += 'Filter: %s %s %s\n' % (filter_name, optr, entry)
        if len(entries) > 1:
            lq_filter += 'Or: %d\n' % len(entries)

    if group_count > 1:
        lq_filter += "And: %d\n" % group_count

    return lq_filter

def match_host_service_url_tmpl(used_filters, row_dict, host_is_ip = False):
    tmpl = 'view.py?view_name=searchsvc&filled_in=filter'
    # Sorry, no support for multiple host- or servicegroups filters in match templates
    for ty, entry in [ ("hostgroup", "host_groups"), ("servicegroup", "service_groups")]:
        if row_dict.get(entry):
            if type(row_dict[entry]) == list:
                row_dict[entry] = row_dict[entry][0]

    for param, key in [                ("service",         "service_description"),
                (host_is_ip and "host_address" or  "host", "host_name"),
                                       ("opthostgroup",    "host_groups"),
                                       ("optservicegroup", "service_groups"),
                                       ("site",            "site")]:
        if row_dict.get(key):
            tmpl_pre = "&%s=%%(%s)s" % (param, key)
            tmpl += tmpl_pre % row_dict
    return tmpl

def search_host_service_url_tmpl(used_filters, data, host_is_ip = False):
    # We combine all used_filters of the same type with (abcd|dfdf)
    filters_combined = {"hosts": [], "services": [], "hostgroups": [], "servicegroups": []}

    for entry in filters_combined.keys():
        for filt in used_filters:
            if filt[0] == entry:
                filters_combined.setdefault(entry, []).append(filt[1].strip())
    for key, value in filters_combined.items():
        if len(value) > 1:
            filters_combined[key] = "(%s)" % "|".join(value)
        elif len(value) == 1:
            filters_combined[key] = value[0]

    tmpl = 'view.py?view_name=searchsvc&filled_in=filter'
    for url_param, qs_name in [        ("service",         "services"     ),
                        host_is_ip and ("host_address",    "host"         )\
                                    or ("host",            "hosts"        ),
                                       ("opthostgroup",    "hostgroups"   ),
                                       ("optservicegroup", "servicegroups")]:
        if filters_combined.get(qs_name):
            tmpl_pre = "&%s=%%(%s)s" % (url_param, qs_name)
            tmpl += tmpl_pre % filters_combined
    return tmpl

search_plugins.append({
    "id"                    : "service_multi",
    "required_types"        : ["services"],
    "optional_types"        : ["hosts", "hostgroups", "servicegroups"],
    "qs_show"               : "service_description",
    "lq_table"              : "services",
    "lq_columns"            : ["service_description", "host_name", "host_groups", "service_groups"],
    "filter_func"           : lambda x: search_host_service_filter(x),
    "match_url_tmpl_func"   : lambda x,y: match_host_service_url_tmpl(x, y),
    "search_url_tmpl_func"  : lambda x,y: search_host_service_url_tmpl(x, y),
})

search_plugins.append({
    "id"                    : "service_multi_address",
    "qs_show"               : "service_description",
    "required_types"        : ["services"],
    "optional_types"        : ["hosts", "hostgroups", "servicegroups"],
    "lq_table"              : "services",
    "lq_columns"            : ["service_description", "host_name", "host_groups", "service_groups", "host_address"],
    "filter_func"           : lambda x: search_host_service_filter(x, host_is_ip = True),
    "match_url_tmpl_func"   : lambda x,y: match_host_service_url_tmpl(x, y, host_is_ip = True),
    "search_url_tmpl_func"  : lambda x,y: search_host_service_url_tmpl(x, y, host_is_ip = True),
})
