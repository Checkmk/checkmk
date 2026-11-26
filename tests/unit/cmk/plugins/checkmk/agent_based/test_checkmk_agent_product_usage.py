#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Product usage analytics reads the agent version from the output of this check

If these tests fail, the output of the "Check_MK Agent" service changed: adapt
cmk/product_usage/collectors/agents.py to the new format.

They cover the summaries of the check plug-in. How the check engine joins the
summaries into the service output is not covered: _plugin_output() assumes it.
"""

from collections.abc import Mapping

from cmk.agent_based.v2 import Result
from cmk.checkengine.checkresults import state_markers
from cmk.plugins.checkmk.agent_based.check_mk import parse_checkmk_labels
from cmk.plugins.checkmk.agent_based.checkmk_agent import (
    check_checkmk_agent,
    check_plugin_checkmk_agent,
)
from cmk.product_usage.collectors.agents import parse_agent_version

_AGENT_SECTION = "Version: 2.3.0p30\nAgentOS: windows\nOSName: Windows\nOSVersion: 10.0.17763"


def _plugin_output(agent_section: str, params: Mapping[str, object]) -> str:
    """The output of the service, assuming the check engine joins and marks the summaries this way"""
    default_params = check_plugin_checkmk_agent.check_default_parameters
    assert default_params is not None
    results = [
        r
        for r in check_checkmk_agent(
            {**default_params, **params},
            parse_checkmk_labels([line.split() for line in agent_section.splitlines()]),
            None,
            None,
            None,
            None,
        )
        if isinstance(r, Result)
    ]
    return ", ".join(
        r.summary + (state_markers[int(r.state)] if len(results) > 1 else "")
        for r in results
        if r.summary
    )


def test_product_usage_reads_the_agent_version_from_the_output() -> None:
    assert parse_agent_version(_plugin_output(_AGENT_SECTION, {})) == "2.3.0p30"


def test_product_usage_reads_the_agent_version_from_the_output_with_a_mismatch() -> None:
    plugin_output = _plugin_output(
        _AGENT_SECTION, {"agent_version": ("specific", {"literal": "2.4.0p15"})}
    )

    assert plugin_output.startswith("Version: 2.3.0p30 (expected 2.4.0p15)(!), ")
    assert parse_agent_version(plugin_output) == "2.3.0p30"


def test_product_usage_reads_no_agent_version_from_an_output_without_one() -> None:
    assert parse_agent_version(_plugin_output("AgentOS: linux", {})) is None
