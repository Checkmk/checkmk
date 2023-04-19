#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.azure_constants import AZURE_REGIONS

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupVMCloudContainer
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import Dictionary, ListChoice


def _region_to_monitor() -> list[tuple[str, str]]:
    def key(regionid_display: tuple[str, str]) -> str:
        return regionid_display[1]

    def is_gov(regionid_display: tuple[str, str]) -> bool:
        return "DoD" in regionid_display[1] or "Gov" in regionid_display[1]

    regions_by_display_order = [
        *sorted((r for r in AZURE_REGIONS.items() if not is_gov(r)), key=key),
        *sorted((r for r in AZURE_REGIONS.items() if is_gov(r)), key=key),
    ]
    return [(id_, f"{region} | {id_}") for id_, region in regions_by_display_order]


def _valuespec_special_agents_azure_status() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "regions",
                ListChoice(
                    title=_("Regions to monitor"),
                    choices=_region_to_monitor(),
                ),
            ),
        ],
        required_keys=["regions"],
        title=_("Microsoft Azure Status"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:azure_status",
        valuespec=_valuespec_special_agents_azure_status,
        doc_references={DocReference.AZURE: _("Monitoring Microsoft Azure")},
    )
)
