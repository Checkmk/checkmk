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


@rulespec_registry.register
class RulespecCheckgroupParametersMssqlDatabases(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "mssql_databases"

    @property
    def title(self):
        return _("MSSQL Databases properties")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("map_db_states",
             Dictionary(
                 elements=[
                     ("ONLINE", MonitoringState(title=_("Database Online"))),
                     ("OFFLINE", MonitoringState(title=_("Database Offline"))),
                     ("RESTORING", MonitoringState(title=_("Database Files are restored"))),
                     ("RECOVERING", MonitoringState(title=_("Database is being recovered"))),
                     ("RECOVERY_PENDING", MonitoringState(title=_("Database must be recovered"))),
                     ("SUSPECT", MonitoringState(title=_("Database Suspect"))),
                     ("EMERGENCY", MonitoringState(title=_("Database changed to emergency"))),
                 ],
                 title=_('Map Database States'),
                 optional_keys=[],
             )),
            ("map_auto_close_state",
             Dictionary(
                 elements=[
                     ("on", MonitoringState(title=_("Auto close on"), default_value=1)),
                     ("off", MonitoringState(title=_("Auto close off"))),
                 ],
                 title=_('Map auto close status'),
                 optional_keys=[],
             )),
            ("map_auto_shrink_state",
             Dictionary(
                 elements=[
                     ("on", MonitoringState(title=_("Auto shrink on"), default_value=1)),
                     ("off", MonitoringState(title=_("Auto shrink off"))),
                 ],
                 title=_('Map auto shrink status'),
                 optional_keys=[],
             )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Database identifier"),)
