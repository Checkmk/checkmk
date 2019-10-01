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


def _item_spec_esx_vsphere_objects():
    return TextAscii(
        title=_("Name of the VM/HostSystem"),
        help=_(
            "Please do not forget to specify either <tt>VM</tt> or <tt>HostSystem</tt>. Example: <tt>VM abcsrv123</tt>. Also note, "
            "that we match the <i>beginning</i> of the name."),
        regex="(^VM|HostSystem)( .*|$)",
        regex_error=_("The name of the system must begin with <tt>VM</tt> or <tt>HostSystem</tt>."),
        allow_empty=False,
    )


def _parameter_valuespec_esx_vsphere_objects():
    return Dictionary(
        help=_("Usually the check goes to WARN if a VM or host is powered off and OK otherwise. "
               "You can change this behaviour on a per-state-basis here."),
        optional_keys=False,
        elements=[
            ("states",
             Dictionary(
                 title=_("Target states"),
                 optional_keys=False,
                 elements=[
                     ("poweredOn",
                      MonitoringState(
                          title=_("Powered ON"),
                          help=_("Check result if the host or VM is powered on"),
                          default_value=0,
                      )),
                     ("poweredOff",
                      MonitoringState(
                          title=_("Powered OFF"),
                          help=_("Check result if the host or VM is powered off"),
                          default_value=1,
                      )),
                     ("suspended",
                      MonitoringState(
                          title=_("Suspended"),
                          help=_("Check result if the host or VM is suspended"),
                          default_value=1,
                      )),
                     ("unknown",
                      MonitoringState(
                          title=_("Unknown"),
                          help=_(
                              "Check result if the host or VM state is reported as <i>unknown</i>"),
                          default_value=3,
                      )),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="esx_vsphere_objects",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_esx_vsphere_objects,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_esx_vsphere_objects,
        title=lambda: _("State of ESX hosts and virtual machines"),
    ))
