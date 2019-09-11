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
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_fireeye_mailq():
    return Dictionary(elements=[
        ("deferred",
         Tuple(
             title=_("Levels for Deferred Queue length"),
             elements=[
                 Integer(title="Warning at", default_value=10, unit="Mails"),
                 Integer(title="Critical at", default_value=15, unit="Mails"),
             ],
         )),
        ("hold",
         Tuple(
             title=_("Levels for Hold Queue length"),
             elements=[
                 Integer(title="Warning at", default_value=500, unit="Mails"),
                 Integer(title="Critical at", default_value=700, unit="Mails"),
             ],
         )),
        ("drop",
         Tuple(
             title=_("Levels for Drop Queue length"),
             elements=[
                 Integer(title="Warning at", default_value=10, unit="Mails"),
                 Integer(title="Critical at", default_value=15, unit="Mails"),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fireeye_mailq",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fireeye_mailq,
        title=lambda: _("Fireeye Mail Queues"),
    ))
