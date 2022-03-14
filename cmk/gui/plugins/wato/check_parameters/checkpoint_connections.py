#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Transform, Tuple


def _parameter_valuespec_checkpoint_connections() -> Transform:
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    Tuple(
                        help=_(
                            "This rule sets limits to the current number of connections through "
                            "a Checkpoint firewall."
                        ),
                        title=_("Maximum number of firewall connections"),
                        elements=[
                            Integer(
                                title=_("Warning at"),
                                minvalue=0,
                                default_value=40000,
                                unit=_("connections"),
                            ),
                            Integer(
                                title=_("Critical at"),
                                minvalue=0,
                                default_value=50000,
                                unit=_("connections"),
                            ),
                        ],
                    ),
                ),
            ],
            optional_keys=False,
        ),
        forth=lambda x: x if isinstance(x, dict) else {"levels": x},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="checkpoint_connections",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_checkpoint_connections,
        title=lambda: _("Checkpoint Firewall Connections"),
    )
)
