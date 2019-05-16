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
    Checkbox,
    Dictionary,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)


@rulespec_registry.register
class RulespecCheckgroupParametersHwFans(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersEnvironment

    @property
    def check_group_name(self):
        return "hw_fans"

    @property
    def title(self):
        return _("FAN speed of Hardware devices")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            elements=[
                (
                    "lower",
                    Tuple(
                        help=_("Lower levels for the fan speed of a hardware device"),
                        title=_("Lower levels"),
                        elements=[
                            Integer(title=_("warning if below"), unit=u"rpm"),
                            Integer(title=_("critical if below"), unit=u"rpm"),
                        ],
                    ),
                ),
                (
                    "upper",
                    Tuple(
                        help=_("Upper levels for the fan speed of a hardware device"),
                        title=_("Upper levels"),
                        elements=[
                            Integer(title=_("warning at"), unit=u"rpm", default_value=8000),
                            Integer(title=_("critical at"), unit=u"rpm", default_value=8400),
                        ],
                    ),
                ),
                ("output_metrics",
                 Checkbox(title=_("Performance data"), label=_("Enable performance data"))),
            ],
            optional_keys=["upper", "output_metrics"],
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("Fan Name"), help=_("The identificator of the fan."))
