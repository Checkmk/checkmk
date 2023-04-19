#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents import common
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, ListChoice


def _valuespec_special_agents_aws_status() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "regions",
                ListChoice(
                    title=_("Regions to monitor"),
                    choices=common.aws_region_to_monitor(),
                ),
            ),
        ],
        required_keys=["regions"],
        title=_("Amazon Web Services (AWS) Status"),
    )


rulespec_registry.register(
    HostRulespec(
        group=common.RulespecGroupVMCloudContainer,
        name="special_agents:aws_status",
        valuespec=_valuespec_special_agents_aws_status,
    )
)
