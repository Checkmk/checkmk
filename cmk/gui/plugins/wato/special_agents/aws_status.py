#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils import aws_constants

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupVMCloudContainer
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, ListChoice


def _valuespec_special_agents_aws_status() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "regions",
                ListChoice(
                    title=_("Regions to monitor"),
                    choices=aws_constants.AWSRegions,
                ),
            ),
        ],
        required_keys=["regions"],
        title=_("Amazon Web Services (AWS) Status"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:aws_status",
        valuespec=_valuespec_special_agents_aws_status,
    )
)
