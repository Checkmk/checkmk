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
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_sym_brightmail_queues():
    return Dictionary(
        help=_("This check is used to monitor successful email delivery through "
               "Symantec Brightmail Scanner appliances."),
        elements=[
            ("connections",
             Tuple(
                 title=_("Number of connections"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
            ("messageRate",
             Tuple(
                 title=_("Number of messages delivered"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
            ("dataRate",
             Tuple(
                 title=_("Amount of data processed"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Cricital at")),
                 ],
             )),
            ("queuedMessages",
             Tuple(
                 title=_("Number of messages currently queued"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
            ("queueSize",
             Tuple(
                 title=_("Size of the queue"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
            ("deferredMessages",
             Tuple(
                 title=_("Number of messages in deferred state"),
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="sym_brightmail_queues",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Instance name"), allow_empty=True),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_sym_brightmail_queues,
        title=lambda: _("Symantec Brightmail Queues"),
    ))
