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
    Alternative,
    Dictionary,
    Integer,
    Percentage,
    RadioChoice,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _parameter_valuespec_cisco_qos():
    return Dictionary(elements=[
        ("unit",
         RadioChoice(
             title=_("Measurement unit"),
             help=_("Here you can specifiy the measurement unit of the network interface"),
             default_value="bit",
             choices=[
                 ("bit", _("Bits")),
                 ("byte", _("Bytes")),
             ],
         )),
        ("post",
         Alternative(
             title=_("Used bandwidth (traffic)"),
             help=_("Settings levels on the used bandwidth is optional. If you do set "
                    "levels you might also consider using averaging."),
             elements=[
                 Tuple(
                     title=_("Percentual levels (in relation to policy speed)"),
                     elements=[
                         Percentage(title=_("Warning at"),
                                    maxvalue=1000,
                                    label=_("% of port speed")),
                         Percentage(title=_("Critical at"),
                                    maxvalue=1000,
                                    label=_("% of port speed")),
                     ],
                 ),
                 Tuple(
                     title=_("Absolute levels in bits or bytes per second"),
                     help=
                     _("Depending on the measurement unit (defaults to bit) the absolute levels are set in bit or byte"
                      ),
                     elements=[
                         Integer(title=_("Warning at"), size=10,
                                 label=_("bits / bytes per second")),
                         Integer(title=_("Critical at"),
                                 size=10,
                                 label=_("bits / bytes per second")),
                     ],
                 )
             ],
         )),
        ("average",
         Integer(
             title=_("Average values"),
             help=_("By activating the computation of averages, the levels on "
                    "errors and traffic are applied to the averaged value. That "
                    "way you can make the check react only on long-time changes, "
                    "not on one-minute events."),
             unit=_("minutes"),
             minvalue=1,
         )),
        ("drop",
         Alternative(
             title=_("Number of dropped bits or bytes per second"),
             help=_(
                 "Depending on the measurement unit (defaults to bit) you can set the warn and crit "
                 "levels for the number of dropped bits or bytes"),
             elements=[
                 Tuple(
                     title=_("Percentual levels (in relation to policy speed)"),
                     elements=[
                         Percentage(title=_("Warning at"),
                                    maxvalue=1000,
                                    label=_("% of port speed")),
                         Percentage(title=_("Critical at"),
                                    maxvalue=1000,
                                    label=_("% of port speed")),
                     ],
                 ),
                 Tuple(elements=[
                     Integer(title=_("Warning at"), size=8, label=_("bits / bytes per second")),
                     Integer(title=_("Critical at"), size=8, label=_("bits / bytes per second")),
                 ],)
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_qos",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("port specification"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cisco_qos,
        title=lambda: _("Cisco quality of service"),
    ))
