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
    FixedValue,
    Integer,
    TextAscii,
    Transform,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersStorage,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersStorage, "multipath_count", _("ESX Multipath Count"),
    Alternative(
        help=_("This rules sets the expected number of active paths for a multipath LUN "
               "on ESX servers"),
        title=_("Match type"),
        elements=[
            FixedValue(
                None,
                title=_("OK if standby count is zero or equals active paths."),
                totext="",
            ),
            Dictionary(
                title=_("Custom settings"),
                elements=[
                    (element,
                     Transform(
                         Tuple(
                             title=description,
                             elements=[
                                 Integer(title=_("Critical if less than")),
                                 Integer(title=_("Warning if less than")),
                                 Integer(title=_("Warning if more than")),
                                 Integer(title=_("Critical if more than")),
                             ]),
                         forth=lambda x: len(x) == 2 and (0, 0, x[0], x[1]) or x))
                    for (element,
                         description) in [("active", _("Active paths")), (
                             "dead", _("Dead paths")), (
                                 "disabled", _("Disabled paths")), (
                                     "standby", _("Standby paths")), ("unknown",
                                                                      _("Unknown paths"))]
                ]),
        ]), TextAscii(title=_("Path ID")), "first")
