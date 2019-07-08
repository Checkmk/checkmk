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
    Optional,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersEnvironment,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


@rulespec_registry.register
class RulespecCheckgroupParametersTemperatureTrends(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersEnvironment

    @property
    def check_group_name(self):
        return "temperature_trends"

    @property
    def title(self):
        return _("Temperature trends for devices with builtin levels")

    @property
    def match_type(self):
        return "dict"

    @property
    def is_deprecated(self):
        return True

    @property
    def parameter_valuespec(self):
        return Dictionary(
            title=_("Temperature Trend Analysis"),
            help=
            _("This rule enables and configures a trend analysis and corresponding limits for devices, "
              "which have their own limits configured on the device. It will only work for supported "
              "checks, right now the <tt>adva_fsp_temp</tt> check."),
            elements=[
                ("trend_range",
                 Optional(Integer(title=_("Time range for temperature trend computation"),
                                  default_value=30,
                                  minvalue=5,
                                  unit=_("minutes")),
                          title=_("Trend computation"),
                          label=_("Enable trend computation"))),
                ("trend_c",
                 Tuple(title=_("Levels on trends in degrees Celsius per time range"),
                       elements=[
                           Integer(title=_("Warning at"),
                                   unit=u"°C / " + _("range"),
                                   default_value=5),
                           Integer(title=_("Critical at"),
                                   unit=u"°C / " + _("range"),
                                   default_value=10)
                       ])),
                ("trend_timeleft",
                 Tuple(title=_("Levels on the time left until limit is reached"),
                       elements=[
                           Integer(
                               title=_("Warning if below"),
                               unit=_("minutes"),
                               default_value=240,
                           ),
                           Integer(
                               title=_("Critical if below"),
                               unit=_("minutes"),
                               default_value=120,
                           ),
                       ])),
            ],
        )

    @property
    def item_spec(self):
        return TextAscii(title=_("Sensor ID"), help=_("The identifier of the thermal sensor."))
