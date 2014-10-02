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

infos['host'] = {
    'title'       : _('Host'),
    'single_spec' : [
        ('host', TextUnicode(
            title = _('Hostname'),
        )),
    ],
}

infos['service'] = {
    'title'       : _('Service'),
    'single_spec' : [
        ('service', TextUnicode(
            title = _('Service Description'),
        )),
    ],
}

infos['hostgroup'] = {
    'title'       : _('Hostgroup'),
    'single_spec' : [ 
        ('hostgroup', TextUnicode(
            title = _('Hostgroup Name'),
        )), 
    ],
}

infos['servicegroup'] = {
    'title'       : _('Servicegroup'),
    'single_spec' : [ 
        ('servicegroup', TextUnicode(
            title = _('Servicegroup Name'),
        )),
    ],
}

infos['log'] = {
    'title'       : _('Log Entry'),
    'single_spec' : None,
}

infos['comment'] = {
    'title'       : _('Comment'),
    'single_spec' : [
        ('comment_id', Integer(
            title = _('Comment ID'),
        )),
    ]
}

infos['downtime'] = {
    'title'       : _('Downtime'),
    'single_spec' : [
        ('downtime_id', Integer(
            title = _('Downtime ID'),
        )),
    ]
}

infos['contact'] = {
    'title'       : _('Contact'),
    'single_spec' : [
        ('contact_name', TextUnicode(
            title = _('Contact Name'),
        )),
    ]
}

infos['command'] = {
    'title'       : _('Command'),
    'single_spec' : [
        ('command_name', TextUnicode(
            title = _('Command Name'),
        )),
    ]
}

infos['aggr'] = {
    'title'       : _('BI Aggregation'),
    'single_spec' : [
        ('aggr_name', TextAscii(
            title = _('Aggregation Name'),
        )),
    ],
}

infos['invswpac'] = {
    'title'       : _('Software Package'),
    'single_spec' : None,
}
