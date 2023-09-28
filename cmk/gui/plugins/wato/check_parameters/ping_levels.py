#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    check_icmp_params,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary


def _valuespec_ping_levels():
    return Dictionary(
        title=_("PING and host check parameters"),
        help=_(
            "This rule sets the parameters for the host checks (via <tt>check_icmp</tt>) "
            "and also for PING checks on ping-only-hosts. For the host checks only the "
            "critical state is relevant, the warning levels are ignored."
        ),
        elements=check_icmp_params(),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        name="ping_levels",
        valuespec=_valuespec_ping_levels,
    )
)
