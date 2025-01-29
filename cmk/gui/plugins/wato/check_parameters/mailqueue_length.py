#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple, ValueSpec

mailqueue_elements: list[tuple[str, ValueSpec]] = [
    (
        "deferred",
        Tuple(
            title=_("Mails in outgoing mail queue/deferred mails"),
            help=_(
                "This rule is applied to the number of E-Mails currently "
                "in the deferred mail queue, or in the general outgoing mail "
                "queue, if such a distinction is not available."
            ),
            elements=[
                Integer(title=_("Warning at"), unit=_("mails"), default_value=10),
                Integer(title=_("Critical at"), unit=_("mails"), default_value=20),
            ],
        ),
    ),
    (
        "active",
        Tuple(
            title=_("Mails in active mail queue"),
            help=_(
                "This rule is applied to the number of E-Mails currently in the active mail queue"
            ),
            elements=[
                Integer(title=_("Warning at"), unit=_("mails"), default_value=800),
                Integer(title=_("Critical at"), unit=_("mails"), default_value=1000),
            ],
        ),
    ),
]


def _parameter_valuespec_mailqueue_length() -> Dictionary:
    return Dictionary(
        elements=mailqueue_elements,
        optional_keys=["active"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mailqueue_length",
        group=RulespecGroupCheckParametersApplications,
        is_deprecated=True,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mailqueue_length,
        title=lambda: _("Mails in outgoing mail queue"),
    )
)
