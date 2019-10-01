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
    DropdownChoice,)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    Levels,
    RulespecGroupCheckParametersOperatingSystem,
)


def _item_spec_vm_counter():
    return DropdownChoice(title=_("kernel counter"),
                          choices=[("Context Switches", _("Context Switches")),
                                   ("Process Creations", _("Process Creations")),
                                   ("Major Page Faults", _("Major Page Faults"))])


def _parameter_valuespec_vm_counter():
    return Levels(
        help=_("This ruleset applies to several similar checks measing various kernel "
               "events like context switches, process creations and major page faults. "
               "Please create separate rules for each type of kernel counter you "
               "want to set levels for."),
        unit=_("events per second"),
        default_levels=(1000, 5000),
        default_difference=(500.0, 1000.0),
        default_value=None,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="vm_counter",
        group=RulespecGroupCheckParametersOperatingSystem,
        is_deprecated=True,
        item_spec=_item_spec_vm_counter,
        parameter_valuespec=_parameter_valuespec_vm_counter,
        title=lambda: _("Number of kernel events per second"),
    ))
