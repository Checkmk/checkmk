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
    Integer,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_pfsense_counter():
    return Dictionary(
        help=_("This rule set is for configuring levels for global packet counters."),
        elements=[
            ("average",
             Integer(
                 title=_("Averaging"),
                 help=_(
                     "When this option is activated then the packet rates are being "
                     "averaged <b>before</b> the levels are being applied. Setting this to zero will "
                     "deactivate averaging."),
                 unit=_("minutes"),
                 default_value=3,
                 minvalue=1,
                 label=_("Compute average over last "),
             )),
            ("fragment",
             Tuple(
                 title=_("Levels for rate of fragmented packets"),
                 elements=[
                     Float(title=_("Warning at"), unit=_("pkts/s"), default_value=100.0),
                     Float(title=_("Critical at"), unit=_("pkts/s"), default_value=10000.0),
                 ],
             )),
            ("normalized",
             Tuple(
                 title=_("Levels for rate of normalized packets"),
                 elements=[
                     Float(title=_("Warning at"), unit=_("pkts/s"), default_value=100.0),
                     Float(title=_("Critical at"), unit=_("pkts/s"), default_value=10000.0),
                 ],
             )),
            ("badoffset",
             Tuple(
                 title=_("Levels for rate of packets with bad offset"),
                 elements=[
                     Float(title=_("Warning at"), unit=_("pkts/s"), default_value=100.0),
                     Float(title=_("Critical at"), unit=_("pkts/s"), default_value=10000.0),
                 ],
             )),
            ("short",
             Tuple(
                 title=_("Levels for rate of short packets"),
                 elements=[
                     Float(title=_("Warning at"), unit=_("pkts/s"), default_value=100.0),
                     Float(title=_("Critical at"), unit=_("pkts/s"), default_value=10000.0),
                 ],
             )),
            ("memdrop",
             Tuple(
                 title=_("Levels for rate of packets dropped due to memory limitations"),
                 elements=[
                     Float(title=_("Warning at"), unit=_("pkts/s"), default_value=100.0),
                     Float(title=_("Critical at"), unit=_("pkts/s"), default_value=10000.0),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="pfsense_counter",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_pfsense_counter,
        title=lambda: _("pfSense Firewall Packet Rates"),
    ))
