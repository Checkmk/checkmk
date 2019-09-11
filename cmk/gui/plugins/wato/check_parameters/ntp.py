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
    Float,
    Integer,
    TextAscii,
    Transform,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersOperatingSystem,
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


def _ntp_params():
    return Tuple(
        title=_("Thresholds for quality of time"),
        elements=[
            Integer(
                title=_("Critical at stratum"),
                default_value=10,
                help=
                _("The stratum (\"distance\" to the reference clock) at which the check gets critical."
                 ),
            ),
            Float(
                title=_("Warning at"),
                unit=_("ms"),
                default_value=200.0,
                help=_("The offset in ms at which a warning state is triggered."),
            ),
            Float(
                title=_("Critical at"),
                unit=_("ms"),
                default_value=500.0,
                help=_("The offset in ms at which a critical state is triggered."),
            ),
        ])


def _item_spec_ntp_peer():
    return TextAscii(title=_("Name of the peer"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ntp_peer",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=_item_spec_ntp_peer,
        parameter_valuespec=_ntp_params,
        title=lambda: _("State of NTP peer"),
    ))


def _parameter_valuespec_ntp_time():
    return Transform(
        Dictionary(elements=[
            (
                "ntp_levels",
                _ntp_params(),
            ),
            ("alert_delay",
             Tuple(title=_("Phases without synchronization"),
                   elements=[
                       Age(
                           title=_("Warning at"),
                           display=["hours", "minutes"],
                           default_value=300,
                       ),
                       Age(
                           title=_("Critical at"),
                           display=["hours", "minutes"],
                           default_value=3600,
                       ),
                   ])),
        ],),
        forth=lambda params: isinstance(params, tuple) and {"ntp_levels": params} or params)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ntp_time",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ntp_time,
        title=lambda: _("State of NTP time synchronisation"),
    ))
