#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, Float, Integer, Percentage, Tuple


def _valuespec_ping_levels() -> Dictionary:
    return Dictionary(
        title=_("Ping and host check parameters"),
        help=_(
            "This rule sets the parameters for the host checks (via <tt>check_icmp</tt>) "
            "and also for ping checks on ping-only-hosts. For the host checks only the "
            "CRITICAL state is relevant, the WARNING levels are ignored."
        ),
        elements=[
            (
                "rta",
                Tuple(
                    title=_("Round trip average"),
                    elements=[
                        Float(title=_("Warning if above"), unit="ms", default_value=200.0),
                        Float(title=_("Critical if above"), unit="ms", default_value=500.0),
                    ],
                ),
            ),
            (
                "loss",
                Tuple(
                    title=_("Packet loss"),
                    help=_(
                        "When the percentage of lost packets is equal or greater then "
                        "this level, then the according state is triggered. The default for critical "
                        "is 100%. That means that the check is only critical if <b>all</b> packets "
                        "are lost."
                    ),
                    elements=[
                        Percentage(title=_("Warning at"), default_value=80.0),
                        Percentage(title=_("Critical at"), default_value=100.0),
                    ],
                ),
            ),
            (
                "packets",
                Integer(
                    title=_("Number of packets"),
                    help=_(
                        "Number ICMP echo request packets to send to the target host on each "
                        "check execution. All packets are sent directly on check execution. Afterwards "
                        "the check waits for the incoming packets."
                    ),
                    minvalue=1,
                    maxvalue=20,
                    default_value=5,
                ),
            ),
            (
                "timeout",
                Integer(
                    title=_("Total timeout of check"),
                    help=_(
                        "After this time (in seconds) the check is aborted, regardless "
                        "of how many packets have been received yet."
                    ),
                    minvalue=1,
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        name="ping_levels",
        valuespec=_valuespec_ping_levels,
    )
)
