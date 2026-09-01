#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ddn_s2a.lib import parse_ddn_s2a_api_response

# The counter names as reported by the API, mapped to the parameter key and the label we use.
_COUNTERS = (
    ("link_failure_errs", "link_failure_errs", "Link failure errors"),
    ("lost_sync_errs", "lost_sync_errs", "Lost sync errors"),
    ("loss_of_sig_errs", "loss_of_signal_errs", "Loss of signal errors"),
    ("prim_seq_errs", "prim_seq_errs", "PrimSeq errors"),  # TODO: What is this?
    ("CRC_errs", "crc_errs", "CRC errors"),
    ("receive_errs", "receive_errs", "Receive errors"),
    ("CTIO_timeouts", "ctio_timeouts", "CTIO timeouts"),
    ("CTIO_xmit_errs", "ctio_xmit_errs", "CTIO transmission errors"),
    ("CTIO_other_errs", "ctio_other_errs", "CTIO other errors"),
)


@dataclass(frozen=True, kw_only=True)
class Port:
    port_type: str
    error_counts: Mapping[str, int]


Section = Mapping[str, Port]


def parse_ddn_s2a_errors(string_table: StringTable) -> Section:
    preparsed = parse_ddn_s2a_api_response(string_table)
    return {
        str(nr + 1): Port(
            port_type=port_type,
            error_counts={key: int(preparsed[api_name][nr]) for api_name, key, _label in _COUNTERS},
        )
        for nr, port_type in enumerate(preparsed["port_type"])
    }


def discover_ddn_s2a_errors(section: Section) -> DiscoveryResult:
    for item, port in section.items():
        # Note: The API command returning the port errors that we evaluate
        #       in this check differentiates between FC and IB ports, providing
        #       different values according to port type. As we have no example
        #       for the IB ports at this time, we only implement logic for what
        #       we can test.
        if port.port_type != "FC":
            continue
        # As the values in this check are all error counters since last reset,
        # we calculate default levels according to the current counter state,
        # so we'll be warned if an error occurs.
        yield Service(
            item=item,
            parameters={key: (count + 1, count + 5) for key, count in port.error_counts.items()},
        )


def check_ddn_s2a_errors(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (port := section.get(item)) is None:
        return

    for _api_name, key, label in _COUNTERS:
        yield _check_error_count(port.error_counts[key], params[key], label)


def _check_error_count(count: int, levels: tuple[int, int] | None, label: str) -> Result:
    if levels is None:
        return Result(state=State.OK, summary=f"{label}: {count}")

    warn, crit = levels
    if count >= crit:
        state = State.CRIT
    elif count >= warn:
        state = State.WARN
    else:
        return Result(state=State.OK, summary=f"{label}: {count}")
    return Result(state=state, summary=f"{label}: {count} (warn/crit at {warn}/{crit} errors)")


agent_section_ddn_s2a_errors = AgentSection(
    name="ddn_s2a_errors",
    parse_function=parse_ddn_s2a_errors,
)


check_plugin_ddn_s2a_errors = CheckPlugin(
    name="ddn_s2a_errors",
    service_name="DDN S2A Port Errors %s",
    discovery_function=discover_ddn_s2a_errors,
    check_function=check_ddn_s2a_errors,
    check_ruleset_name="ddn_s2a_port_errors",
    check_default_parameters={},
)
