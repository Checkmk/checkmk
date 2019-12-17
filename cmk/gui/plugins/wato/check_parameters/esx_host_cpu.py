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
    Percentage,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)


def _parameter_valuespec_esx_host_memory():
    return Dictionary(elements=[
        ("cpu_ready",
         Tuple(
             title=_("CPU ready"),
             elements=[
                 Percentage(title=_("Warning at a CPU ready time of"), default_value=5.0),
                 Percentage(title=_("Critical at a CPU ready time of"), default_value=10.0),
             ],
         )),
        ("cpu_costop",
         Tuple(
             title=_("Co-Stop"),
             elements=[
                 Percentage(title=_("Warning at a Co-Stop time of"), default_value=5.0),
                 Percentage(title=_("Critical at a Co-Stop time of"), default_value=10.0),
             ],
         )),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="esx_host_cpu",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_esx_host_memory,
        title=lambda: _("CPU usage of ESX host system"),
    ))
