#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    Integer,
    MonitoringState,
    OptionalDropdownChoice,
    Percentage,
    TextInput,
    Transform,
    Tuple,
)


def websphere_mq_common_elements():
    return [
        (
            "message_count",
            OptionalDropdownChoice(
                title=_("Maximum number of messages"),
                choices=[(None, _("Ignore these levels"))],
                otherlabel=_("Set absolute levels"),
                explicit=Tuple(
                    title=_("Maximum number of messages"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
                default_value=(1000, 1200),
            ),
        ),
        (
            "message_count_perc",
            OptionalDropdownChoice(
                title=_("Percentage of queue length"),
                help=_("This setting only applies if the WebSphere MQ reports the queue length"),
                choices=[(None, _("Ignore these levels"))],
                otherlabel=_("Set relative levels"),
                explicit=Tuple(
                    title=_("Percentage of queue length"),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
                default_value=(80.0, 90.0),
            ),
        ),
    ]


def transform_websphere_mq_queues(source):
    if isinstance(source, tuple):
        return {"message_count": source}
    if "messages_not_processed_age" in source:
        age_params = source["messages_not_processed_age"]
        source["messages_not_processed"] = {}
        source["messages_not_processed"]["age"] = age_params
        del source["messages_not_processed_age"]
        return source
    return source


def _parameter_valuespec_websphere_mq():
    return Transform(
        valuespec=Dictionary(
            elements=websphere_mq_common_elements()
            + [
                (
                    "messages_not_processed",
                    Dictionary(
                        title=_("Settings for messages not processed"),
                        help=_(
                            "With this rule you can determine the warn and crit age "
                            "if LGETTIME and LGETDATE is available in the agent data. "
                            "Note that if LGETTIME and LGETDATE are available but not set "
                            "you can set the service state which is default WARN. "
                            "This rule applies only if the current depth is greater than zero."
                        ),
                        elements=[
                            (
                                "age",
                                Tuple(
                                    title=_("Upper levels for the age"),
                                    elements=[
                                        Age(title=_("Warning at")),
                                        Age(title=_("Critical at")),
                                    ],
                                ),
                            ),
                            (
                                "state",
                                MonitoringState(
                                    title=_(
                                        "State if LGETTIME and LGETDATE are available but not set"
                                    ),
                                    default_value=1,
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        ),
        forth=transform_websphere_mq_queues,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="websphere_mq",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of queue")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_websphere_mq,
        title=lambda: _("Websphere MQ"),
    )
)
