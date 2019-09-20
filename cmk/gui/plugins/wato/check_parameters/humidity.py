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
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)


def transform_humidity(p):
    if isinstance(p, (list, tuple)):
        p = {
            "levels_lower": (float(p[1]), float(p[0])),
            "levels": (float(p[2]), float(p[3])),
        }
    return p


def _item_spec_humidity():
    return TextAscii(
        title=_("Sensor name"),
        help=_("The identifier of the sensor."),
    )


def _parameter_valuespec_humidity():
    return Transform(
        Dictionary(
            help=_("This Ruleset sets the threshold limits for humidity sensors"),
            elements=[
                ("levels",
                 Tuple(
                     title=_("Upper levels"),
                     elements=[
                         Percentage(title=_("Warning at")),
                         Percentage(title=_("Critical at")),
                     ],
                 )),
                ("levels_lower",
                 Tuple(
                     title=_("Lower levels"),
                     elements=[
                         Percentage(title=_("Warning below")),
                         Percentage(title=_("Critical below")),
                     ],
                 )),
            ],
        ),
        forth=transform_humidity,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="humidity",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_humidity,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_humidity,
        title=lambda: _("Humidity Levels"),
    ))
