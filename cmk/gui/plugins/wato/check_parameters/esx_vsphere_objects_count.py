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
    Integer,
    ListOf,
    ListOfStrings,
    MonitoringState,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_esx_vsphere_objects_count():
    return Dictionary(
        optional_keys=False,
        elements=[
            ("distribution",
             ListOf(
                 Dictionary(
                     optional_keys=False,
                     elements=[("vm_names", ListOfStrings(title=_("VMs"))),
                               ("hosts_count", Integer(title=_("Number of hosts"),
                                                       default_value=2)),
                               ("state",
                                MonitoringState(title=_("State if violated"), default_value=1))],
                 ),
                 title=_("VM distribution"),
                 help=_(
                     "You can specify lists of VM names and a number of hosts,"
                     " to make sure the specfied VMs are distributed across at least so many hosts."
                     " E.g. provide two VM names and set 'Number of hosts' to two,"
                     " to make sure those VMs are not running on the same host."))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="esx_vsphere_objects_count",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_esx_vsphere_objects_count,
        title=lambda: _("Distribution of virtual machines over ESX hosts"),
    ))
