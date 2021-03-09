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
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_varnish_fetch():
    return Dictionary(elements=[
        ("1xx",
         Tuple(
             title=_("Upper levels for \"fetch no body (1xx)\" per second"),
             elements=[
                 Float(title=_("Warning at"), default_value=1.0, allow_empty=False),
                 Float(title=_("Critical at"), default_value=2.0, allow_empty=False)
             ],
         )),
        ("204",
         Tuple(
             title=_("Upper levels for \"fetch no body (204)\" per second"),
             elements=[
                 Float(title=_("Warning at"), default_value=1.0, allow_empty=False),
                 Float(title=_("Critical at"), default_value=2.0, allow_empty=False)
             ],
         )),
        ("304",
         Tuple(
             title=_("Upper levels for \"fetch no body (304)\" per second"),
             elements=[
                 Float(title=_("Warning at"), default_value=1.0, allow_empty=False),
                 Float(title=_("Critical at"), default_value=2.0, allow_empty=False)
             ],
         )),
        ("bad",
         Tuple(
             title=_("Upper levels for \"fetch had bad headers\" per second"),
             elements=[
                 Float(title=_("Warning at"), default_value=1.0, allow_empty=False),
                 Float(title=_("Critical at"), default_value=2.0, allow_empty=False)
             ],
         )),
        ("eof",
         Tuple(
             title=_("Upper levels for \"fetch EOF\" per second"),
             elements=[
                 Float(title=_("Warning at"), default_value=1.0, allow_empty=False),
                 Float(title=_("Critical at"), default_value=2.0, allow_empty=False)
             ],
         )),
        ("failed",
         Tuple(
             title=_("Upper levels for \"fetch failed\" per second"),
             elements=[
                 Float(title=_("Warning at"), default_value=1.0, allow_empty=False),
                 Float(title=_("Critical at"), default_value=2.0, allow_empty=False)
             ],
         )),
        ("zero",
         Tuple(
             title=_("Upper levels for \"fetch zero length\" per second"),
             elements=[
                 Float(title=_("Warning at"), default_value=1.0, allow_empty=False),
                 Float(title=_("Critical at"), default_value=2.0, allow_empty=False)
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="varnish_fetch",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_varnish_fetch,
        title=lambda: _("Varnish Fetch"),
    ))
