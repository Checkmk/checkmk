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
    Age,
    Dictionary,
    Integer,
    MonitoringState,
    OptionalDropdownChoice,
    Percentage,
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def websphere_mq_common_elements():
    return [
        ("message_count",
         OptionalDropdownChoice(title=_('Maximum number of messages'),
                                choices=[(None, _("Ignore these levels"))],
                                otherlabel=_("Set absolute levels"),
                                explicit=Tuple(title=_('Maximum number of messages'),
                                               elements=[
                                                   Integer(title=_("Warning at")),
                                                   Integer(title=_("Critical at")),
                                               ]),
                                default_value=(1000, 1200))),
        ("message_count_perc",
         OptionalDropdownChoice(
             title=_('Percentage of queue length'),
             help=_('This setting only applies if the WebSphere MQ reports the queue length'),
             choices=[(None, _("Ignore these levels"))],
             otherlabel=_("Set relative levels"),
             explicit=Tuple(title=_('Percentage of queue length'),
                            elements=[
                                Percentage(title=_("Warning at")),
                                Percentage(title=_("Critical at")),
                            ]),
             default_value=(80.0, 90.0))),
    ]


def transform_websphere_mq_queues(source):
    if isinstance(source, tuple):
        return {"message_count": source}
    elif "messages_not_processed_age" in source:
        age_params = source["messages_not_processed_age"]
        source["messages_not_processed"] = {}
        source["messages_not_processed"]["age"] = age_params
        del source["messages_not_processed_age"]
        return source
    return source


def _parameter_valuespec_websphere_mq():
    return Transform(Dictionary(elements=websphere_mq_common_elements() + [
        ("messages_not_processed",
         Dictionary(
             title=_("Settings for messages not processed"),
             help=_("With this rule you can determine the warn and crit age "
                    "if LGETTIME and LGETDATE is available in the agent data. "
                    "Note that if LGETTIME and LGETDATE are available but not set "
                    "you can set the service state which is default WARN. "
                    "This rule applies only if the current depth is greater than zero."),
             elements=[
                 ("age",
                  Tuple(
                      title=_("Upper levels for the age"),
                      elements=[
                          Age(title=_("Warning at")),
                          Age(title=_("Critical at")),
                      ],
                  )),
                 ("state",
                  MonitoringState(
                      title=_("State if LGETTIME and LGETDATE are available but not set"),
                      default_value=1)),
             ],
         )),
    ],),
                     forth=transform_websphere_mq_queues)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="websphere_mq",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of queue")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_websphere_mq,
        title=lambda: _("Websphere MQ"),
    ))
