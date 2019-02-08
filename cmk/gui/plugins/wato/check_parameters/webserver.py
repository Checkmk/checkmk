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
    Float,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


@rulespec_registry.register
class RulespecCheckgroupParametersWebserver(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "webserver"

    @property
    def title(self):
        return _("Azure web servers (IIS)")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            elements=[
                (
                    "avg_response_time_levels",
                    Tuple(
                        title=_("Upper levels for average response time"),
                        elements=[
                            Float(title=_("Warning at"), default_value=1.00, unit="s"),
                            Float(title=_("Critical at"), default_value=10.0, unit="s"),
                        ],
                    ),
                ),
                (
                    "error_rate_levels",
                    Tuple(
                        title=_("Upper levels for rate of server errors"),
                        elements=[
                            Float(title=_("Warning at"), default_value=0.01, unit="1/s"),
                            Float(title=_("Critical at"), default_value=0.04, unit="1/s"),
                        ],
                    ),
                ),
                (
                    "cpu_time_percent_levels",
                    Tuple(
                        title=_("Upper levels for CPU time"),
                        elements=[
                            Float(title=_("Warning at"), default_value=85., unit="%"),
                            Float(title=_("Critical at"), default_value=95., unit="%"),
                        ],
                    ),
                ),
            ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Name of the service"))
