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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.valuespec import (TextUnicode, Integer)

from cmk.gui.plugins.visuals import declare_info

declare_info(
    'host',
    {
        'title': _('Host'),
        'title_plural': _('Hosts'),
        'single_spec': [('host', TextUnicode(title=_('Hostname'),))],
        # When these filters are set, the site hint will not be added to urls
        # which link to views using this datasource, because the resuling view
        # should show the objects spread accross the sites
        "multiple_site_filters": ["hostgroup"],
    })

declare_info(
    'service',
    {
        'title': _('Service'),
        'title_plural': _('Services'),
        'single_spec': [('service', TextUnicode(title=_('Service Description'),))],
        # When these filters are set, the site hint will not be added to urls
        # which link to views using this datasource, because the resuling view
        # should show the objects spread accross the sites
        "multiple_site_filters": ["servicegroup"],
    })

declare_info(
    'hostgroup',
    {
        'title': _('Host Group'),
        'title_plural': _('Host Groups'),
        'single_site': False,  # spread over multiple sites
        'single_spec': [('hostgroup', TextUnicode(title=_('Host Group Name'),))],
    })

declare_info(
    'servicegroup',
    {
        'title': _('Service Group'),
        'title_plural': _('Service Groups'),
        'single_site': False,  # spread over multiple sites
        'single_spec': [('servicegroup', TextUnicode(title=_('Service Group Name'),)),],
    })

declare_info('log', {
    'title': _('Log Entry'),
    'title_plural': _('Log Entries'),
    'single_spec': None,
})

declare_info(
    'comment', {
        'title': _('Comment'),
        'title_plural': _('Comments'),
        'single_spec': [('comment_id', Integer(title=_('Comment ID'),)),]
    })

declare_info(
    'downtime', {
        'title': _('Downtime'),
        'title_plural': _('Downtimes'),
        'single_spec': [('downtime_id', Integer(title=_('Downtime ID'),)),]
    })

declare_info(
    'contact', {
        'title': _('Contact'),
        'title_plural': _('Contacts'),
        'single_spec': [('log_contact_name', TextUnicode(title=_('Contact Name'),)),]
    })

declare_info(
    'command', {
        'title': _('Command'),
        'title_plural': _('Commands'),
        'single_spec': [('command_name', TextUnicode(title=_('Command Name'),)),]
    })

declare_info(
    'aggr', {
        'title': _('BI Aggregation'),
        'title_plural': _('BI Aggregations'),
        'single_spec': [('aggr_name', TextUnicode(title=_('Aggregation Name'),)),],
    })

declare_info(
    'aggr_group', {
        'title': _('BI Aggregation Group'),
        'title_plural': _('BI Aggregation Groups'),
        'single_spec': [('aggr_group', TextUnicode(title=_('Aggregation group'),)),],
    })

declare_info('discovery', {
    'title': _('Discovery Output'),
    'title_plural': _('Discovery Outputs'),
    'single_spec': None,
})

if config.mkeventd_enabled:
    declare_info(
        'event', {
            'title': _('Event Console Event'),
            'title_plural': _('Event Console Events'),
            'single_spec': [('event_id', Integer(title=_('Event ID'),)),]
        })

    declare_info(
        'history', {
            'title': _('Historic Event Console Event'),
            'title_plural': _('Historic Event Console Events'),
            'single_spec': [
                ('event_id', Integer(title=_('Event ID'),)),
                ('history_line', Integer(title=_('History Line Number'),)),
            ]
        })
