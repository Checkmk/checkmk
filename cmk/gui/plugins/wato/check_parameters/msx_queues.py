#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Dictionary, Integer, ListOf, TextInput, Transform, Tuple


def transform_msx_queues(params):
    if isinstance(params, tuple):
        return {"levels": (params[0], params[1])}
    return params


def transform_msx_queues_inventory(params):
    if isinstance(params, list):
        # do not overwrite default discovery parameters with empty list
        return (
            {
                "queue_names": params,
            }
            if params
            else {}
        )
    return params


def _valuespec_winperf_msx_queues_inventory():
    return Transform(
        valuespec=Dictionary(
            title=_("Queue names"),
            elements=[
                (
                    "queue_names",
                    ListOf(
                        valuespec=Tuple(
                            orientation="horizontal",
                            elements=[
                                TextInput(
                                    title=_("Name of Queue"),
                                    size=50,
                                    allow_empty=False,
                                ),
                                Integer(
                                    title=_("Offset"),
                                    help=_(
                                        "The offset of the information relative to counter base."
                                        " You can get a detailed list of available counters in a windows shell with the command 'lodctr /s:counters.txt'."
                                    ),
                                ),
                            ],
                        ),
                        title=_("MS Exchange message queues discovery"),
                        help=_(
                            "Per default the offsets of all Windows performance counters are preconfigured in the check. "
                            "If the format of your counters object is not compatible then you can adapt the counter "
                            "offsets manually."
                        ),
                        movable=False,
                        add_label=_("Add Counter"),
                    ),
                )
            ],
        ),
        forth=transform_msx_queues_inventory,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="winperf_msx_queues_inventory",
        valuespec=_valuespec_winperf_msx_queues_inventory,
    )
)


def _item_spec_msx_queues():
    return TextInput(
        title=_("Explicit Queue Names"),
        help=_("Specify queue names that the rule should apply to"),
    )


def _parameter_valuespec_msx_queues():
    return Transform(
        valuespec=Dictionary(
            title=_("Set Levels"),
            elements=[
                (
                    "levels",
                    Tuple(
                        title=_("Maximum Number of E-Mails in Queue"),
                        elements=[
                            Integer(title=_("Warning at"), unit=_("E-Mails")),
                            Integer(title=_("Critical at"), unit=_("E-Mails")),
                        ],
                    ),
                ),
                (
                    "offset",
                    Integer(
                        title=_("Offset"),
                        help=_(
                            "This parameter should only be used for enforced services, otherwise it will be determined by the discovery rule <i>Microsoft Exchange Queues Discovery</i>."
                        ),
                    ),
                ),
            ],
        ),
        forth=transform_msx_queues,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="msx_queues",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_msx_queues,
        parameter_valuespec=_parameter_valuespec_msx_queues,
        title=lambda: _("MS Exchange Message Queues"),
    )
)
