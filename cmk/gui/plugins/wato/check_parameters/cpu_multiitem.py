#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice


def _valuespec_cpu_utilization_multiitem_discovery():
    return Dictionary(
        title=_("CPU multi item discovery"),
        help=_(
            "This rule controls which and how many checks will be created "
            "for monitoring individual CPUs. "
            "Currently only cisco_cpu_multiitem supports this configuration. "
        ),
        elements=[
            (
                "average",
                DropdownChoice(
                    title=_("Discover a service checking the average of all CPUs"),
                    choices=[(True, _("Discover")), (False, _("Do not discover"))],
                ),
            ),
            (
                "individual",
                DropdownChoice(
                    title=_("Discover individual services for each CPU"),
                    choices=[(True, _("Discover")), (False, _("Do not discover"))],
                ),
            ),
        ],
        default_keys=["individual"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        name="cpu_utilization_multiitem_discovery",
        valuespec=_valuespec_cpu_utilization_multiitem_discovery,
    )
)
