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
    Age,
    Dictionary,
    Integer,
    MonitoringState,
    Percentage,
    Transform,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersEnvironment,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


@rulespec_registry.register
class RulespecCheckgroupParametersApcSymentra(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersEnvironment

    @property
    def check_group_name(self):
        return "apc_symentra"

    @property
    def title(self):
        return _("APC Symmetra Checks")

    @property
    def parameter_valuespec(self):
        return Transform(
            Dictionary(
                elements=[
                    ("capacity",
                     Tuple(title=_("Levels of battery capacity"),
                           elements=[
                               Percentage(
                                   title=_("Warning below"),
                                   default_value=95.0,
                               ),
                               Percentage(
                                   title=_("Critical below"),
                                   default_value=90.0,
                               ),
                           ])),
                    ("calibration_state",
                     MonitoringState(
                         title=_("State if calibration is invalid"),
                         default_value=0,
                     )),
                    ("post_calibration_levels",
                     Dictionary(
                         title=_("Levels of battery parameters after calibration"),
                         help=
                         _("After a battery calibration the battery capacity is reduced until the "
                           "battery is fully charged again. Here you can specify an alternative "
                           "lower level in this post-calibration phase. "
                           "Since apc devices remember the time of the last calibration only "
                           "as a date, the alternative lower level will be applied on the whole "
                           "day of the calibration until midnight. You can extend this time period "
                           "with an additional time span to make sure calibrations occuring just "
                           "before midnight do not trigger false alarms."),
                         elements=[
                             ("altcapacity",
                              Percentage(
                                  title=_(
                                      "Alternative critical battery capacity after calibration"),
                                  default_value=50,
                              )),
                             ("additional_time_span",
                              Integer(
                                  title=("Extend post-calibration phase by additional time span"),
                                  unit=_("minutes"),
                                  default_value=0,
                              )),
                         ],
                         optional_keys=False,
                     )),
                    ("battime",
                     Tuple(
                         title=_("Time left on battery"),
                         elements=[
                             Age(title=_("Warning at"),
                                 help=
                                 _("Time left on Battery at and below which a warning state is triggered"
                                  ),
                                 default_value=0,
                                 display=["hours", "minutes"]),
                             Age(title=_("Critical at"),
                                 help=
                                 _("Time Left on Battery at and below which a critical state is triggered"
                                  ),
                                 default_value=0,
                                 display=["hours", "minutes"]),
                         ],
                     )),
                    ("battery_replace_state",
                     MonitoringState(
                         title=_("State if battery needs replacement"),
                         default_value=1,
                     )),
                ],
                optional_keys=['post_calibration_levels', 'output_load', 'battime'],
            ),
            forth=self._transform_apc_symmetra,
        )

    def _transform_apc_symmetra(self, params):
        if isinstance(params, (list, tuple)):
            params = {"levels": params}

        if "levels" in params and len(params["levels"]) > 2:
            cap = float(params["levels"][0])
            params["capacity"] = (cap, cap)
            del params["levels"]

        if "output_load" in params:
            del params["output_load"]

        return params
