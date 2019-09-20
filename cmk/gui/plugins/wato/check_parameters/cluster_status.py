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
    DropdownChoice,
    MonitoringState,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_cluster_status():
    return Dictionary(
        elements=[
            ("type",
             DropdownChoice(title=_("Cluster type"),
                            help=_("Expected cluster type."),
                            choices=[
                                ("active_standby", _("active / standby")),
                                ("active_active", _("active / active")),
                            ],
                            default_value="active_standby")),
            ("v11_2_states",
             Dictionary(
                 title=_("Interpretation of failover cluster state"),
                 help=_("Here you can set the failover state for BIG-IP system of version 11.2.0"),
                 elements=[
                     ("0", MonitoringState(title="Unknown", default_value=3)),
                     ("1", MonitoringState(title="Offline", default_value=2)),
                     ("2", MonitoringState(title="Forced offline", default_value=2)),
                     ("3", MonitoringState(title="Standby", default_value=0)),
                     ("4", MonitoringState(title="Active", default_value=0)),
                 ],
             ))
        ],
        required_keys=["type"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cluster_status",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cluster_status,
        title=lambda: _("Cluster status"),
    ))
