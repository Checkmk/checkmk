#!/usr/bin/env python
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
    Tuple,
    Integer,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _item_spec_mtr():
    return TextAscii(title=_("MTR destination"),
                     help=_("Specify the name of the destination host, i.e. <tt>checkmk.com</tt>"),
                     allow_empty=False)


def _parameter_valuespec_mtr():
    return Dictionary(
        help=_(
            "This ruleset can be used to change MTR's (Matt's traceroute) warning and crit levels for packet loss, average "
            "roundtrip and standard deviation."),
        elements=[
            ("avg",
             Tuple(
                 title=_("Average roundtrip time in ms"),
                 elements=[
                     Integer(title=_("Warning at"), default_value=150, unit=_("ms"), min_value=0),
                     Integer(title=_("Critical at"), default_value=250, unit=_("ms"), min_value=0),
                 ],
                 help=_(
                     "The maximum average roundtrip time in ms before this service goes into warning/critical. "
                     "This alarm only applies to the target host, not the hops in between."),
             )),
            ("stddev",
             Tuple(
                 title=_("Standard deviation of roundtrip times in ms"),
                 elements=[
                     Integer(title=_("Warning at"), default_value=150, unit=_("ms"), min_value=0),
                     Integer(title=_("Critical at"), default_value=250, unit=_("ms"), min_value=0),
                 ],
                 help=
                 _("The maximum standard deviation on the roundtrip time in ms before this service goes into"
                   "warning/critical. This alarm only applies to the target host, not the hops in between."
                  ),
             )),
            ("loss",
             Tuple(
                 title=_("Packet loss in percentage"),
                 elements=[
                     Integer(title=_("Warning at"), default_value=10, unit=_("%"), min_value=0),
                     Integer(title=_("Critical at"), default_value=25, unit=_("%"), min_value=0),
                 ],
                 help=_(
                     "The maximum allowed percentage of packet loss to the destination before this service "
                     "goes into warning/critical."),
             )),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mtr",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=_item_spec_mtr,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mtr,
        title=lambda: _("Traceroute with MTR"),
    ))
