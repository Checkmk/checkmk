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
    ListOf,
    Percentage,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupManualChecksNetworking,
    rulespec_registry,
    ManualCheckParameterRulespec,
)


# TODO: Why is this only a manual check rulespec?
def _parameter_valuespec_cpu_utilization_cluster():
    return ListOf(
        Tuple(elements=[
            Integer(title=_("Equal or more than"), unit=_("nodes")),
            Tuple(
                elements=[
                    Percentage(title=_("Warning at a utilization of"), default_value=90.0),
                    Percentage(title=_("Critical at a utilization of"), default_value=95.0)
                ],
                title=_("Alert on too high CPU utilization"),
            )
        ]),
        help=_(
            "Configure levels for averaged CPU utilization depending on number of cluster nodes. "
            "The CPU utilization sums up the percentages of CPU time that is used "
            "for user processes and kernel routines over all available cores within "
            "the last check interval. The possible range is from 0% to 100%"),
        title=_("Memory Usage"),
        add_label=_("Add limits"),
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="cpu_utilization_cluster",
        group=RulespecGroupManualChecksNetworking,
        parameter_valuespec=_parameter_valuespec_cpu_utilization_cluster,
        title=lambda: _("CPU Utilization of Clusters"),
    ))
