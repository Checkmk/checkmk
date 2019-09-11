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
    Integer,
    Percentage,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupManualChecksApplications,
    rulespec_registry,
    ManualCheckParameterRulespec,
)


def _item_spec_wmic_process():
    return TextAscii(
        title=_("Process name for usage in the Nagios service description"),
        allow_empty=False,
    )


def _parameter_valuespec_wmic_process():
    return Tuple(elements=[
        TextAscii(
            title=_("Name of the process"),
            allow_empty=False,
        ),
        Integer(title=_("Memory warning at"), unit="MB"),
        Integer(title=_("Memory critical at"), unit="MB"),
        Integer(title=_("Pagefile warning at"), unit="MB"),
        Integer(title=_("Pagefile critical at"), unit="MB"),
        Percentage(title=_("CPU usage warning at")),
        Percentage(title=_("CPU usage critical at")),
    ],)


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="wmic_process",
        group=RulespecGroupManualChecksApplications,
        item_spec=_item_spec_wmic_process,
        parameter_valuespec=_parameter_valuespec_wmic_process,
        title=lambda: _("Memory and CPU of processes on Windows"),
    ))
