#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.gui.valuespec import Dictionary, Integer, ListOf, TextInput, Tuple


def _valuespec_winperf_msx_queues_inventory() -> Dictionary:
    return Dictionary(
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
                                    " You can get a detailed list of available counters in a Windows shell with the command 'lodctr /s:counters.txt'."
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
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="winperf_msx_queues_inventory",
        valuespec=_valuespec_winperf_msx_queues_inventory,
    )
)


def _item_spec_msx_queues() -> TextInput:
    return TextInput(
        title=_("Explicit Queue Names"),
        help=_("Specify queue names that the rule should apply to"),
    )


def _parameter_valuespec_msx_queues() -> Dictionary:
    return Dictionary(
        title=_("Set levels"),
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Maximum number of emails in queue"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("Emails")),
                        Integer(title=_("Critical at"), unit=_("Emails")),
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
