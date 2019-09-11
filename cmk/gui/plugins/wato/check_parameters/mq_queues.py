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


def _item_spec_mq_queues():
    return TextAscii(title=_("Queue Name"),
                     help=_("The name of the queue like in the Apache queue manager"))


def _parameter_valuespec_mq_queues():
    return Dictionary(elements=[
        ("size",
         Tuple(
             title=_("Levels for the queue length"),
             help=_("Set the maximum and minimum length for the queue size"),
             elements=[
                 Integer(title="Warning at a size of"),
                 Integer(title="Critical at a size of"),
             ],
         )),
        ("consumerCount",
         Tuple(
             title=_("Levels for the consumer count"),
             help=_("Consumer Count is the size of connected consumers to a queue"),
             elements=[
                 Integer(title="Warning less then"),
                 Integer(title="Critical less then"),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mq_queues",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_mq_queues,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mq_queues,
        title=lambda: _("Apache ActiveMQ Queue lengths"),
    ))
