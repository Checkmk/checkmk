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

try:
    mkeventd_enabled = config.mkeventd_enabled
except:
    mkeventd_enabled = False

# Declare datasource only if the event console is activated. We do
# not want to irritate users that do not know anything about the EC.
if mkeventd_enabled:
    context_types['mkeventd_event'] = {
        'title'      : _('Single Event Console Event'),
        'single'     : True,
        'parameters' : [
            ('event_id', Integer(
                title = _('Event ID'),
            )),
        ],
    }

    context_types['mkeventd_events'] = {
        'title'      : _('Multiple Event Console Events'),
        'single'     : False,
        'parameters' : VisualFilterList(['event', 'host']),
    }

    context_types['mkeventd_history_event'] = {
        'title'      : _('Single Event Console Event (History)'),
        'single'     : True,
        'parameters' : [
            ('event_id', Integer(
                title = _('Event ID'),
            )),
            ('history_line', Integer(
                title = _('History Line'),
            )),
        ],
    }

    context_types['mkeventd_history_events'] = {
        'title'      : _('Multiple Event Console Events (History)'),
        'single'     : False,
        'parameters' : VisualFilterList(['history', 'event', 'host']),
    }
