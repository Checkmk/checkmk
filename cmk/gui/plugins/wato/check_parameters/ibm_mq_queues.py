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
    OptionalDropdownChoice,
    Percentage,
    TextInput,
    Tuple,
)


def _parameter_valuespec_ibm_mq_queues():
    return Dictionary(
        help=_(
            "See 'Queue status attributes' in IBM manual"
            "(https://www.ibm.com/support/knowledgecenter/en/SSFKSJ_9.2.0/com.ibm.mq.explorer.doc/e_status_queue.html)"
            " for detailed explanations of these parameters."
        ),
        elements=[
            (
                "curdepth",
                OptionalDropdownChoice(
                    title=_("Current queue depth"),
                    help=_("CURDEPTH: The number of messages currently on the queue."),
                    choices=[((None, None), _("Ignore these levels"))],
                    otherlabel=_("Set absolute levels"),
                    explicit=Tuple(
                        title=_("Maximum number of messages"),
                        elements=[
                            Integer(title=_("Warning at")),
                            Integer(title=_("Critical at")),
                        ],
                    ),
                ),
            ),
            (
                "curdepth_perc",
                OptionalDropdownChoice(
                    help=_(
                        "CURDEPTH_PERC: Percentage (CURDEPTH/MAXDEPTH) of the number of"
                        " messages currently on the queue."
                    ),
                    title=_("Current queue depth in %"),
                    choices=[((None, None), _("Ignore these levels"))],
                    otherlabel=_("Set relative levels"),
                    default_value=(80.0, 90.0),
                    explicit=Tuple(
                        title=_("Percentage of queue depth"),
                        elements=[
                            Percentage(title=_("Warning at")),
                            Percentage(title=_("Critical at")),
                        ],
                    ),
                ),
            ),
            (
                "msgage",
                Tuple(
                    help=_("MSGAGE: The age, in seconds, of the oldest message on the queue."),
                    title=_("Oldest message age"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "lgetage",
                Tuple(
                    help=_(
                        "The age, in seconds, when the last message was retrieved from the queue."
                        " Calculated by subtracting LGETDATE/LGETTIME from current timestamp."
                    ),
                    title=_("Last get age"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "lputage",
                Tuple(
                    help=_(
                        "The age, in seconds, when the last message was put to the queue. "
                        " Calculated by subtracting LPUTDATE/LPUTTIME from current timestamp."
                    ),
                    title=_("Last put age"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "ipprocs",
                Dictionary(
                    help=_(
                        "IPPROCS: The number of applications that are currently connected to"
                        " the queue to get messages from the queue."
                    ),
                    title=_("Open input count"),
                    elements=[
                        (
                            "lower",
                            Tuple(
                                title=_("Lower levels"),
                                elements=[
                                    Integer(title=_("Warning if below")),
                                    Integer(title=_("Critical if below")),
                                ],
                            ),
                        ),
                        (
                            "upper",
                            Tuple(
                                title=_("Upper levels"),
                                elements=[
                                    Integer(title=_("Warning at")),
                                    Integer(title=_("Critical at")),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
            (
                "opprocs",
                Dictionary(
                    help=_(
                        "OPPROCS: The number of applications that are currently connected"
                        " to the queue to put messages on the queue."
                    ),
                    title=_("Open output count"),
                    elements=[
                        (
                            "lower",
                            Tuple(
                                title=_("Lower levels"),
                                elements=[
                                    Integer(title=_("Warning if below")),
                                    Integer(title=_("Critical if below")),
                                ],
                            ),
                        ),
                        (
                            "upper",
                            Tuple(
                                title=_("Upper levels"),
                                elements=[
                                    Integer(title=_("Warning at")),
                                    Integer(title=_("Critical at")),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ibm_mq_queues",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of Queue")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_mq_queues,
        title=lambda: _("IBM MQ Queues"),
    )
)
