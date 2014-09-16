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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

context_types['global'] = {
    'title'      : _('Global (no specific context)'),
    'single'     : False,
    'parameters' : None,
}

context_types['host'] = {
    'title'      : _('Single Host'),
    'single'     : True,
    'infos'      : [ "host" ],
    'parameters' : [
        ('host', TextUnicode(
            title = _('Hostname'),
        )),
    ],
}

context_types['hosts'] = {
    'title'      : _('Multiple Hosts'),
    'single'     : False,
    'infos'      : [ "host" ],
    'parameters' : VisualFilterList(['host']),
}

context_types['service'] = {
    'title'      : _('Single Service'),
    'infos'      : [ "host", "service" ],
    'single'     : True,
    'parameters' : [
        ('host', TextUnicode(
                title = _('Hostname'),
        )),
        ('service', TextUnicode(
                title = _('Service Description'),
        )),
    ],
}

context_types['services'] = {
    'title'      : _('Multiple Services'),
    'single'     : False,
    'infos'      : [ "host", "service" ],
    'parameters' : VisualFilterList(['service', 'host']),
}

context_types['service_on_hosts'] = {
    'title'      : _('Single Service on multiple hosts'),
    'single'     : True,
    'infos'      : [ "service" ],
    'parameters' : [
        ('service', TextUnicode(
            title = _('Service Description'),
        )),
    ],
}

context_types['hostgroup'] = {
    'title'      : _('Single Hostgroups'),
    'single'     : True,
    'infos'      : [ "hostgroup" ],
    'parameters' : [
        ('hostgroup', TextUnicode(
            title = _('Hostgroup Name'),
        )),
    ],
}

context_types['hostgroups'] = {
    'title'      : _('Multiple Hostgroups'),
    'single'     : False,
    'infos'      : [ "hostgroup" ],
    'parameters' : VisualFilterList(['hostgroup', 'hostgroups']),
}

context_types['servicegroup'] = {
    'title'      : _('Single Servicegroups'),
    'single'     : True,
    'infos'      : [ "servicegroup" ],
    'parameters' : [
        ('servicegroup', TextUnicode(
            title = _('Servicegroup Name'),
        )),
    ],
}

context_types['servicegroups'] = {
    'title'      : _('Multiple Servicegroups'),
    'single'     : False,
    'infos'      : [ "servicegroup" ],
    'parameters' : VisualFilterList(['servicegroup']),
}

context_types['comments'] = {
    'title'      : _('Multiple Comments'),
    'single'     : False,
    'infos'      : [ "host", "service" ],
    'parameters' : VisualFilterList(['comment', 'host', 'service']),
}

context_types['downtimes'] = {
    'title'      : _('Multiple Downtimes'),
    'single'     : False,
    'infos'      : [ "host", "service" ],
    'parameters' : VisualFilterList(['downtime', 'host', 'service']),
}

context_types['logs'] = {
    'title'      : _('Multiple Log Entries'),
    'single'     : False,
    'infos'      : [ "log", "host", "service" ],
    'parameters' : VisualFilterList(['log', 'host', 'service', 'contact', 'command']),
}

context_types['logs_contact'] = {
    'title'      : _('Single Contact Log Entry'),
    'single'     : True,
    'infos'      : [ "log", "host", "service" ],
    'parameters' : [
        ('log_contact_name', TextAscii(
            title = _('Contact Name'),
        )),
    ],
}

context_types['bi_aggregation'] = {
    'title'      : _('Single BI Aggregation'),
    'single'     : True,
    'infos'      : [ "aggr" ],
    'parameters' : [
        ('aggr_name', TextAscii(
            title = _('Aggregation Name'),
        )),
    ],
}

context_types['bi_aggregations'] = {
    'title'      : _('Multiple BI Aggregations'),
    'single'     : False,
    'infos'      : [ "aggr" ],
    'parameters' : VisualFilterList(['aggr']),
}

context_types['bi_host_aggregation'] = {
    'title'      : _('Single BI Aggregation affected by one host'),
    'single'     : True,
    'infos'      : [ "aggr", "host" ],
    'parameters' : [
        ('aggr_host', TextAscii(
            title = _('Hostname'),
        )),
    ],
}

context_types['bi_host_aggregations'] = {
    'title'      : _('Multiple Single Host BI Aggregations'),
    'single'     : False,
    'infos'      : [ "aggr", "host" ],
    'parameters' : VisualFilterList(['aggr', 'host']),
}

context_types['bi_hostname_aggregations'] = {
    'title'      : _('Multiple Single Host BI Aggregations (Aggregation name joined)'),
    'single'     : False,
    'infos'      : [ "aggr", "host" ],
    'parameters' : VisualFilterList(['aggr', 'host']),
}

context_types['bi_aggregation_group'] = {
    'title'      : _('Single BI Aggregation group'),
    'single'     : True,
    'infos'      : [ "aggr" ],
    'parameters' : [
        ('aggr_group', TextAscii(
            title = _('Hostname'),
        )),
    ],
}

context_types['invswpacs'] = {
    'title'      : _('Multiple Software Packages'),
    'single'     : False,
    "infos"      : [ "host", "invswpac" ],
    'parameters' : VisualFilterList(['invswpac', 'host']),
}
