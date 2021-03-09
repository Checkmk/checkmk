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
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_docker_node_containers():
    return Dictionary(
        help=_(
            "Allows to define absolute levels for all, running, paused, and stopped containers."),
        elements=[
            ("upper_levels",
             Tuple(
                 title=_("Containers upper levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ],
             )),
            ("lower_levels",
             Tuple(
                 title=_("Containers lower levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ],
             )),
            ("running_upper_levels",
             Tuple(
                 title=_("Running containers upper levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ],
             )),
            ("running_lower_levels",
             Tuple(
                 title=_("Running containers lower levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ],
             )),
            ("paused_upper_levels",
             Tuple(
                 title=_("Paused containers upper levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ],
             )),
            ("paused_lower_levels",
             Tuple(
                 title=_("Paused containers lower levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ],
             )),
            ("stopped_upper_levels",
             Tuple(
                 title=_("Stopped containers upper levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ],
             )),
            ("stopped_lower_levels",
             Tuple(
                 title=_("Stopped containers lower levels"),
                 elements=[
                     Integer(title=_("Warning at"), allow_empty=False),
                     Integer(title=_("Critical at"), allow_empty=False),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="docker_node_containers",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_docker_node_containers,
        title=lambda: _("Docker node container levels"),
    ))
