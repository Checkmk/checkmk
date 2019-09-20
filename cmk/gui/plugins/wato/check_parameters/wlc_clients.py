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
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _parameter_valuespec_wlc_clients():
    return Transform(
        Dictionary(title=_("Number of connections"),
                   elements=[
                       ("levels",
                        Tuple(title=_("Upper levels"),
                              elements=[
                                  Integer(title=_("Warning at"), unit=_("connections")),
                                  Integer(title=_("Critical at"), unit=_("connections")),
                              ])),
                       ("levels_lower",
                        Tuple(title=_("Lower levels"),
                              elements=[
                                  Integer(title=_("Critical if below"), unit=_("connections")),
                                  Integer(title=_("Warning if below"), unit=_("connections")),
                              ])),
                   ]),
        # old params = (crit_low, warn_low, warn, crit)
        forth=lambda v: isinstance(v, tuple) and {
            "levels": (
                v[2],
                v[3],
            ),
            "levels_lower": (
                v[1],
                v[0],
            )
        } or v,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="wlc_clients",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("Name of Wifi")),
        parameter_valuespec=_parameter_valuespec_wlc_clients,
        title=lambda: _("WLC WiFi client connections"),
    ))
