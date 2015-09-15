#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
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

infos['host'] = {
    'title'       : _('Host'),
    'title_plural': _('Hosts'),
    'single_spec' : [
        ('host', TextUnicode(
            title = _('Hostname'),
        )),
    ],
}

infos['service'] = {
    'title'       : _('Service'),
    'title_plural': _('Services'),
    'single_spec' : [
        ('service', TextUnicode(
            title = _('Service Description'),
        )),
    ],
}

infos['hostgroup'] = {
    'title'       : _('Host Group'),
    'title_plural': _('Host Groups'),
    'single_site' : False, # spread over multiple sites
    'single_spec' : [
        ('hostgroup', TextUnicode(
            title = _('Host Group Name'),
        )),
    ],
}

infos['servicegroup'] = {
    'title'       : _('Service Group'),
    'title_plural': _('Service Groups'),
    'single_site' : False, # spread over multiple sites
    'single_spec' : [
        ('servicegroup', TextUnicode(
            title = _('Service Group Name'),
        )),
    ],
}

infos['log'] = {
    'title'       : _('Log Entry'),
    'title_plural': _('Log Entries'),
    'single_spec' : None,
}

infos['comment'] = {
    'title'       : _('Comment'),
    'title_plural': _('Comments'),
    'single_spec' : [
        ('comment_id', Integer(
            title = _('Comment ID'),
        )),
    ]
}

infos['downtime'] = {
    'title'       : _('Downtime'),
    'title_plural': _('Downtimes'),
    'single_spec' : [
        ('downtime_id', Integer(
            title = _('Downtime ID'),
        )),
    ]
}

infos['contact'] = {
    'title'       : _('Contact'),
    'title_plural': _('Contacts'),
    'single_spec' : [
        ('log_contact_name', TextUnicode(
            title = _('Contact Name'),
        )),
    ]
}

infos['command'] = {
    'title'       : _('Command'),
    'title_plural': _('Commands'),
    'single_spec' : [
        ('command_name', TextUnicode(
            title = _('Command Name'),
        )),
    ]
}

infos['aggr'] = {
    'title'       : _('BI Aggregation'),
    'title_plural': _('BI Aggregations'),
    'single_spec' : [
        ('aggr_name', TextAscii(
            title = _('Aggregation Name'),
        )),
    ],
}

