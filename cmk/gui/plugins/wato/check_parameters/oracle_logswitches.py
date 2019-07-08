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
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def transform_oracle_logswitches(params):
    if isinstance(params, tuple):
        return {
            'levels': (params[2], params[3]),
            'levels_lower': (params[1], params[0]),
        }
    return params


@rulespec_registry.register
class RulespecCheckgroupParametersOracleLogswitches(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "oracle_logswitches"

    @property
    def title(self):
        return _("Oracle Logswitches")

    @property
    def parameter_valuespec(self):
        return Transform(
            Dictionary(
                help=_("This check monitors the number of log switches of an ORACLE "
                       "database instance in the last 60 minutes. You can set levels "
                       "for upper and lower bounds."),
                elements=[
                    (
                        'levels',
                        Tuple(
                            title=_("Set upper Levels"),
                            elements=[
                                Integer(title=_("Warning at or above"),
                                        unit=_("log switches / hour"),
                                        default_value=50),
                                Integer(title=_("Critical at or above"),
                                        unit=_("log switches / hour"),
                                        default_value=100),
                            ],
                        ),
                    ),
                    (
                        'levels_lower',
                        Tuple(
                            title=_("Set lower Levels"),
                            elements=[
                                Integer(title=_("Warning at or below"),
                                        unit=_("log switches / hour"),
                                        default_value=-1),
                                Integer(title=_("Critical at or below"),
                                        unit=_("log switches / hour"),
                                        default_value=-1),
                            ],
                        ),
                    ),
                ],
            ),
            forth=transform_oracle_logswitches,
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("Database SID"), size=12, allow_empty=False)
