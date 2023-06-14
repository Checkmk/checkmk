#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils import gcp_constants

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupVMCloudContainer
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, ListChoice


def _regions_to_monitor() -> list[tuple[str, str]]:
    return [(k, f"{k} | {v}") for k, v in sorted(gcp_constants.RegionMap.items())]


def _valuespec_special_agents_gcp_status() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "regions",
                ListChoice(
                    title=_("Regions to monitor"),
                    choices=_regions_to_monitor(),
                ),
            ),
        ],
        title=_("Google Cloud Platform (GCP) Status"),
        required_keys=["regions"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:gcp_status",
        valuespec=_valuespec_special_agents_gcp_status,
    )
)
