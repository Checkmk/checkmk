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

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    ListOfStrings,
    MonitoringState,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "services_summary", _("Windows Service Summary"),
    Dictionary(
        title=_('Autostart Services'),
        elements=[
            ('ignored',
             ListOfStrings(
                 title=_("Ignored autostart services"),
                 help=_('Regular expressions matching the begining of the internal name '
                        'or the description of the service. '
                        'If no name is given then this rule will match all services. The '
                        'match is done on the <i>beginning</i> of the service name. It '
                        'is done <i>case sensitive</i>. You can do a case insensitive match '
                        'by prefixing the regular expression with <tt>(?i)</tt>. Example: '
                        '<tt>(?i).*mssql</tt> matches all services which contain <tt>MSSQL</tt> '
                        'or <tt>MsSQL</tt> or <tt>mssql</tt> or...'),
                 orientation="horizontal",
             )),
            ('state_if_stopped',
             MonitoringState(
                 title=_("Default state if stopped autostart services are found"),
                 default_value=0,
             )),
        ],
    ), None, "dict")
