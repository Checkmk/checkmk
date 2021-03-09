#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Percentage, Transform, Tuple


def _parameter_valuespec_checkpoint_connections() -> Transform:
    return Transform(
        Dictionary(
            [
                (
                    "levels",
                    Tuple(
                        help=_("This rule sets limits to the current number of connections through "
                               "a Checkpoint firewall."),
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
                (
                    "relative_levels",
                    Tuple(
                        title=_("Percentage of maximum connections (only used if a limit is "
                                "defined on the Check Point device)"),
                        help=
                        _("This relative threshold can only be used if a maximum number is defined on "
                          "the firewall side and then read from fwConnTableLimit. By default, this "
                          "limit is not set in Check Point devices and this check than falls back to "
                          "the absolute defaults or the ones defined above"),
                        elements=[
                            Percentage(
                                title=_("Warning at"),
                                unit="%",
                                minvalue=0.0,
                                default_value=80.0,
                            ),
                            Percentage(
                                title=_("Critical at"), unit="%", minvalue=0.0, default_value=90.0),
                        ]),
                ),
            ],
            optional_keys=["relative_levels"],
        ),
        forth=lambda x: x if isinstance(x, dict) else {"levels": x},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="checkpoint_connections",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_checkpoint_connections,
        title=lambda: _("Checkpoint Firewall Connections"),
    ))
