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
    defines,
    Dictionary,
    ListOfTimeRanges,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)


def _item_spec_motion():
    return TextAscii(
        title=_("Sensor name"),
        help=_("The identifier of the sensor."),
    )


def _parameter_valuespec_motion():
    return Dictionary(elements=[
        ("time_periods",
         Dictionary(
             title=_("Time periods"),
             help=_("Specifiy time ranges during which no motion is expected. "
                    "Outside these times, the motion detector will always be in "
                    "state OK"),
             elements=[(day_id, ListOfTimeRanges(title=day_str))
                       for day_id, day_str in defines.weekdays_by_name()],
             optional_keys=[],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="motion",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_motion,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_motion,
        title=lambda: _("Motion Detectors"),
    ))
