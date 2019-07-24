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
    Float,
    DualListChoice,
    MonitoringState,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.check_parameters.mssql_blocked_sessions import mssql_waittypes


@rulespec_registry.register
class RulespecCheckgroupParametersMssqlInstanceBlockedSessions(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "mssql_instance_blocked_sessions"

    @property
    def title(self):
        return _("MSSQL Blocked Sessions")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("state",
             MonitoringState(
                 title=_("State if at least one blocked session"),
                 default_value=2,
             )),
            ("waittime",
             Tuple(
                 title=_("Levels for wait"),
                 help=_("The threshholds for wait_duration_ms. Will "
                        "overwrite the default state set above."),
                 default_value=(0, 0),
                 elements=[
                     Float(title=_("Warning at"), unit=_("seconds"), display_format="%.3f"),
                     Float(title=_("Critical at"), unit=_("seconds"), display_format="%.3f"),
                 ],
             )),
            ("ignore_waittypes",
             DualListChoice(
                 title=_("Ignore wait types"),
                 rows=40,
                 choices=[(entry, entry) for entry in mssql_waittypes],
             )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Instance identifier"))
