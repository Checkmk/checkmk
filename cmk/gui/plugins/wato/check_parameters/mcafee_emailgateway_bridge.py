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
from cmk.gui.valuespec import Dictionary, Float, Tuple


def _parameter_valuespec_mcafee_emailgateway_bridge():
    return Dictionary(
        elements=[
            (
                "tcp",
                Tuple(
                    title=_("TCP packets"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("packets/s")),
                        Float(title=_("Critical at"), unit=_("packets/s")),
                    ],
                ),
            ),
            (
                "udp",
                Tuple(
                    title=_("UDP packets"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("packets/s")),
                        Float(title=_("Critical at"), unit=_("packets/s")),
                    ],
                ),
            ),
            (
                "icmp",
                Tuple(
                    title=_("ICMP packets"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("packets/s")),
                        Float(title=_("Critical at"), unit=_("packets/s")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mcafee_emailgateway_bridge",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mcafee_emailgateway_bridge,
        title=lambda: _("McAfee email gateway bridge"),
    )
)
