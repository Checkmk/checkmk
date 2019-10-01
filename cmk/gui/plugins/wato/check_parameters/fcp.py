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
    CascadingDropdown,
    Dictionary,
    OptionalDropdownChoice,
    Integer,
    ListOf,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    Levels,
    RulespecGroupCheckParametersNetworking,
)

from cmk.gui.plugins.wato.check_parameters.utils import vs_interface_traffic


def _parameter_valuespec_fcp():
    return Dictionary(elements=[
        ("speed",
         OptionalDropdownChoice(title=_("Operating speed"),
                                help=_(
                                    "If you use this parameter then the check goes warning if the "
                                    "interface is not operating at the expected speed (e.g. it "
                                    "is working with 8Gbit/s instead of 16Gbit/s)."),
                                choices=[
                                    (None, _("ignore speed")),
                                    (4000000000, "4 Gbit/s"),
                                    (8000000000, "8 Gbit/s"),
                                    (16000000000, "16 Gbit/s"),
                                ],
                                otherlabel=_("specify manually ->"),
                                explicit=Integer(title=_("Other speed in bits per second"),
                                                 label=_("Bits per second")))),
        ("traffic",
         ListOf(
             CascadingDropdown(
                 title=_("Direction"),
                 orientation="horizontal",
                 choices=[
                     ('both', _("In / Out"), vs_interface_traffic()),
                     ('in', _("In"), vs_interface_traffic()),
                     ('out', _("Out"), vs_interface_traffic()),
                 ],
             ),
             title=_("Used bandwidth (minimum or maximum traffic)"),
             help=_("Setting levels on the used bandwidth is optional. If you do set "
                    "levels you might also consider using averaging."),
         )),
        ("read_latency",
         Levels(title=_("Read latency"),
                unit=_("ms"),
                default_value=None,
                default_levels=(50.0, 100.0))),
        ("write_latency",
         Levels(title=_("Write latency"),
                unit=_("ms"),
                default_value=None,
                default_levels=(50.0, 100.0))),
        ("latency",
         Levels(title=_("Overall latency"),
                unit=_("ms"),
                default_value=None,
                default_levels=(50.0, 100.0))),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fcp",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("Port specification"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fcp,
        title=lambda: _("Fibrechannel Interfaces"),
    ))
