#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupVMCloudContainer
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import FixedValue


def _valuespec_special_agents_gcp_status() -> FixedValue:
    # CMK-8322
    return FixedValue(
        value={},
        title=_("Google Cloud Platform (GCP) Status"),
        help=_("This special agent does not require any configuration."),
        totext=_("Deploy the special agent"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:gcp_status",
        valuespec=_valuespec_special_agents_gcp_status,
    )
)
