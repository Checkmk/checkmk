#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import CascadingDropdown, Dictionary


def _valuespec_discovery_netapp_api_psu_rules():
    return Dictionary(
        title=_("Netapp power supply unit discovery"),
        elements=[
            (
                "mode",
                CascadingDropdown(
                    title=_("Specify discovery mode"),
                    help=_(
                        "Option which allows to specify whether all power supply units will be grouped into one service (summary) or each unit gets allocated one individual service (single)."
                    ),
                    orientation="vertical",
                    choices=[
                        ("summarize", _("Summary")),
                        ("single", _("Single")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="discovery_netapp_api_psu_rules",
        valuespec=_valuespec_discovery_netapp_api_psu_rules,
    )
)
