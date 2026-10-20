# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
"""Per-conductor residual current; the summary module owns shared evaluation."""

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult
)
from cmk.plugins.raritan.lib import PduSection
from cmk.plugins.raritan.agent_based.raritan_pdu_residual_current_summary import (
    check_residual_current_section,
    discover_residual_current,
    Params,
)


def discover_raritan_pdu_residual_current(
        section: PduSection
) -> DiscoveryResult:
    yield from discover_residual_current(section.get_residual())


def check_raritan_pdu_residual_current(
        item: str,
        params: Params,
        section: PduSection
) -> CheckResult:
    yield from check_residual_current_section(item, params, section)


check_plugin_raritan_pdu_residual_current = CheckPlugin(
    name="raritan_pdu_residual_current",
    sections=["raritan_pdu_inlet"],
    service_name="Residual Current %s",
    discovery_function=discover_raritan_pdu_residual_current,
    check_function=check_raritan_pdu_residual_current,
    check_ruleset_name="residual_current",
    check_default_parameters=Params(warn_missing_data=True, warn_missing_levels=True),
)
