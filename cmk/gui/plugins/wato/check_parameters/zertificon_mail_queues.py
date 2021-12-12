#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupEnforcedServicesApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec() -> Dictionary:
    return Dictionary(
        title=_("Upper levels for queue lengths"),
        elements=[
            (
                queue,
                Tuple(
                    title=_("Levels for %s mail queue") % queue,
                    help=_("Upper levels for %s mail queue") % queue,
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            default_value=50,
                            unit=_("mails"),
                            minvalue=0,
                        ),
                        Integer(
                            title=_("Critical at"),
                            default_value=100,
                            unit=_("mails"),
                            minvalue=0,
                        ),
                    ],
                ),
            )
            for queue in [
                "postfix",
                "incoming",
                "active",
                "deferred",
                "hold",
                "maildrop",
                "z1",
            ]
        ],
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="zertificon_mail_queues",
        group=RulespecGroupEnforcedServicesApplications,
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Zertificon Mail Queues"),
    )
)
