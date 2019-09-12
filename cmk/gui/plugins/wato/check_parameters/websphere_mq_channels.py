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
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.check_parameters.websphere_mq import websphere_mq_common_elements


def _parameter_valuespec_websphere_mq_channels():
    return Dictionary(elements=websphere_mq_common_elements() + [
        ("status",
         Dictionary(
             title=_('Override check state based on channel state'),
             elements=[
                 ("INACTIVE",
                  MonitoringState(title=_("State when channel is inactive"), default_value=2)),
                 ("INITIALIZING",
                  MonitoringState(title=_("State when channel is initializing"), default_value=2)),
                 ("BINDING",
                  MonitoringState(title=_("State when channel is binding"), default_value=2)),
                 ("STARTING",
                  MonitoringState(title=_("State when channel is starting"), default_value=2)),
                 ("RUNNING",
                  MonitoringState(title=_("State when channel is running"), default_value=0)),
                 ("RETRYING",
                  MonitoringState(title=_("State when channel is retrying"), default_value=2)),
                 ("STOPPING",
                  MonitoringState(title=_("State when channel is stopping"), default_value=2)),
                 ("STOPPED",
                  MonitoringState(title=_("State when channel is stopped"), default_value=1)),
                 ("other",
                  MonitoringState(title=_("State when channel status is unknown"),
                                  default_value=2)),
             ],
             optional_keys=[],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="websphere_mq_channels",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of channel")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_websphere_mq_channels,
        title=lambda: _("Websphere MQ Channels"),
    ))
