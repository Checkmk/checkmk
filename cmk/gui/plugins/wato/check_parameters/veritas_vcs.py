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


def _parameter_valuespec_veritas_vcs():
    return Dictionary(elements=[
        ("map_states",
         Dictionary(
             title=_("Map Attribute 'State'"),
             elements=[
                 ("ONLINE", MonitoringState(title=_("ONLINE"), default_value=0)),
                 ("RUNNING", MonitoringState(title=_("RUNNING"), default_value=0)),
                 ("OK", MonitoringState(title=_("OK"), default_value=0)),
                 ("OFFLINE", MonitoringState(title=_("OFFLINE"), default_value=1)),
                 ("EXITED", MonitoringState(title=_("EXITED"), default_value=1)),
                 ("PARTIAL", MonitoringState(title=_("PARTIAL"), default_value=1)),
                 ("FAULTED", MonitoringState(title=_("FAULTED"), default_value=2)),
                 ("UNKNOWN", MonitoringState(title=_("UNKNOWN"), default_value=3)),
                 ("default", MonitoringState(title=_("States other than the above"),
                                             default_value=1)),
             ],
             optional_keys=False,
         )),
        ("map_frozen",
         Dictionary(
             title=_("Map Attribute 'Frozen'"),
             elements=[
                 ("tfrozen", MonitoringState(title=_("Temporarily frozen"), default_value=1)),
                 ("frozen", MonitoringState(title=_("Frozen"), default_value=2)),
             ],
             optional_keys=False,
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="veritas_vcs",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Cluster Name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_veritas_vcs,
        title=lambda: _("Veritas Cluster Server"),
    ))
