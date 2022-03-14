#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.mailqueue_length import mailqueue_elements
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Transform, Tuple

mailqueue_params = Dictionary(
    elements=[
        *mailqueue_elements,
        (
            "failed",
            Tuple(
                title=_("Mails in failed mail queue"),
                help=_(
                    "This rule is applied to the number of E-Mails currently "
                    "in the failed mail queue"
                ),
                elements=[
                    Integer(title=_("Warning at"), unit=_("mails"), default_value=1),
                    Integer(title=_("Critical at"), unit=_("mails"), default_value=1),
                ],
            ),
        ),
    ],
    optional_keys=["active", "deferred", "failed"],
)


def _parameter_valuespec_mail_queue_length():
    return Transform(
        valuespec=mailqueue_params,
        forth=lambda old: not isinstance(old, dict) and {"deferred": old} or old,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mail_queue_length",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Mail queue name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mail_queue_length,
        title=lambda: _("Mails in outgoing mail queue"),
    )
)
