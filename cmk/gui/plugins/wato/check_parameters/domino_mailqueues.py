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
from cmk.gui.valuespec import Dictionary, DropdownChoice, Integer, Tuple


def _item_spec_domino_mailqueues():
    return DropdownChoice(
        choices=[
            ("lnDeadMail", _("Mails in Dead Queue")),
            ("lnWaitingMail", _("Mails in Waiting Queue")),
            ("lnMailHold", _("Mails in Hold Queue")),
            ("lnMailTotalPending", _("Total Pending Mails")),
            ("InMailWaitingforDNS", _("Mails Waiting for DNS Queue")),
        ],
        title=_("Domino Mail Queue Names"),
    )


def _parameter_valuespec_domino_mailqueues():
    return Dictionary(
        elements=[
            (
                "queue_length",
                Tuple(
                    title=_("Number of Mails in Queue"),
                    elements=[
                        Integer(title=_("warning at"), default_value=300),
                        Integer(title=_("critical at"), default_value=350),
                    ],
                ),
            ),
        ],
        required_keys=["queue_length"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="domino_mailqueues",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_domino_mailqueues,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_domino_mailqueues,
        title=lambda: _("Lotus Domino Mail Queues"),
    )
)
