#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<iptables>>>
# -A INPUT -j RH-Firewall-1-INPUT
# -A FORWARD -j RH-Firewall-1-INPUT
# ...
# COMMIT


import difflib
import hashlib
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)


def iptables_hash(config: str) -> str:
    return hashlib.sha256(config.encode("utf-8")).hexdigest()


def parse_iptables(string_table: StringTable) -> str:
    config_lines = [" ".join(sublist) for sublist in string_table]
    return "\n".join(config_lines)


def discover_iptables(section: str) -> DiscoveryResult:
    yield Service(parameters={"config_hash": iptables_hash(section)})


def check_iptables(params: Mapping[str, Any], section: str) -> CheckResult:
    value_store = get_value_store()
    item_state = value_store.get("iptables.config")

    if not item_state:
        value_store["iptables.config"] = {"config": section, "hash": iptables_hash(section)}
        raise IgnoreResultsError(
            "Initial configuration has been saved. The next check interval will contain a valid state."
        )

    initial_config_hash = params["config_hash"]
    new_config_hash = iptables_hash(section)

    if initial_config_hash == new_config_hash:
        if initial_config_hash != item_state.get("hash"):
            value_store["iptables.config"] = {"config": section, "hash": new_config_hash}
            yield Result(
                state=State.OK, summary="accepted new filters after service rediscovery / reboot"
            )
            return
        yield Result(state=State.OK, summary="no changes in filters table detected")
        return

    reference_config = item_state["config"].splitlines()
    actual_config = section.splitlines()
    diff = difflib.context_diff(
        reference_config, actual_config, fromfile="before", tofile="after", lineterm=""
    )
    diff_output = "\n".join(diff)

    yield Result(
        state=State.CRIT,
        summary="changes in filters table detected",
        details=f"changes in filters table detected\n{diff_output}",
    )


agent_section_iptables = AgentSection(
    name="iptables",
    parse_function=parse_iptables,
)

check_plugin_iptables = CheckPlugin(
    name="iptables",
    service_name="Iptables",
    discovery_function=discover_iptables,
    check_function=check_iptables,
    check_default_parameters={},
)
