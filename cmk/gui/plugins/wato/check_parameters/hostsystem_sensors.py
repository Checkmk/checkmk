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
    ListOf,
    MonitoringState,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)


@rulespec_registry.register
class RulespecCheckgroupParametersHostsystemSensors(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersEnvironment

    @property
    def check_group_name(self):
        return "hostsystem_sensors"

    @property
    def title(self):
        return _("Hostsystem sensor alerts")

    @property
    def parameter_valuespec(self):
        return ListOf(Dictionary(
            help=_("This rule allows to override alert levels for the given sensor names."),
            elements=[
                ("name", TextAscii(title=_("Sensor name"))),
                ("states",
                 Dictionary(
                     title=_("Custom states"),
                     elements=[(element,
                                MonitoringState(title="Sensor %s" % description,
                                                label=_("Set state to"),
                                                default_value=int(element)))
                               for (element, description) in [("0", _("OK")), (
                                   "1", _("WARNING")), ("2", _("CRITICAL")), ("3", _("UNKNOWN"))]],
                 ))
            ],
            optional_keys=False),
                      add_label=_("Add sensor name"))
