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
    MonitoringState,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _parameter_valuespec_cisco_stack():
    return Dictionary(
        elements=[
            ("waiting",
             MonitoringState(title=u"waiting",
                             default_value=0,
                             help=_(u"Waiting for other switches to come online"))),
            ("progressing",
             MonitoringState(title=u"progressing",
                             default_value=0,
                             help=_(u"Master election or mismatch checks in progress"))),
            ("added", MonitoringState(title=u"added", default_value=0, help=_(u"Added to stack"))),
            ("ready", MonitoringState(title=u"ready", default_value=0, help=_(u"Ready"))),
            ("sdmMismatch",
             MonitoringState(title=u"sdmMismatch",
                             default_value=1,
                             help=_(u"SDM template mismatch"))),
            ("verMismatch",
             MonitoringState(title=u"verMismatch", default_value=1,
                             help=_(u"OS version mismatch"))),
            ("featureMismatch",
             MonitoringState(title=u"featureMismatch",
                             default_value=1,
                             help=_(u"Configured feature mismatch"))),
            ("newMasterInit",
             MonitoringState(title=u"newMasterInit",
                             default_value=0,
                             help=_(u"Waiting for new master initialization"))),
            ("provisioned",
             MonitoringState(title=u"provisioned",
                             default_value=0,
                             help=_(u"Not an active member of the stack"))),
            ("invalid",
             MonitoringState(title=u"invalid",
                             default_value=2,
                             help=_(u"State machine in invalid state"))),
            ("removed",
             MonitoringState(title=u"removed", default_value=2, help=_(u"Removed from stack"))),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_stack",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("Switch number"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cisco_stack,
        title=lambda: _("Cisco Stack Switch Status"),
    ))
