#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ported by (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from contextlib import suppress
from datetime import datetime, timedelta, UTC
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    render,
    Result,
    State,
    StringTable,
)
from cmk.agent_based.v3_unstable import discover_one_service
from cmk.plugins.prism.lib import load_json
from cmk.plugins.prism.v4_models import Alert, Alerts

Section = Sequence[Mapping[Any, Any]]
Params = Mapping[str, object]

PRISM_CENTRAL_VM = "Prism Central VM"


def _alert(
    context: dict[str, Any], message: str, timestamp: int, severity: str
) -> Mapping[str, Any]:
    with suppress(KeyError):
        message = message.format(**context)
    return {
        **context,
        "timestamp": timestamp,
        "severity": severity,
        "message": message.replace("\n", ", "),
    }


def _legacy_context(entity: Mapping[str, Any]) -> dict[str, Any]:
    context = dict(zip(entity["context_types"], entity["context_values"]))
    if any(
        affected.get("entity_type") == "prism_central_vm"
        for affected in entity.get("affected_entities") or []
    ):
        context["vm_type"] = PRISM_CENTRAL_VM
    return context


def parse_prism_alerts(string_table: StringTable) -> Section:
    return [
        _alert(
            _legacy_context(entity),
            entity["message"],
            entity["created_time_stamp_in_usecs"],
            entity["severity"],
        )
        for entity in load_json(string_table).get("entities", {})
    ]


agent_section_prism_alerts = AgentSection(
    name="prism_alerts",
    parse_function=parse_prism_alerts,
)

_SEVERITIES = {"INFO": "kInfo", "WARNING": "kWarning", "CRITICAL": "kCritical"}
_EPOCH = datetime.fromtimestamp(0, UTC)


def _context(alert: Alert) -> dict[str, Any]:
    context: dict[str, Any] = {
        parameter.param_name: value
        for parameter in alert.parameters
        if parameter.param_name is not None
        and (value := parameter.param_value.as_text()) is not None
    }
    if alert.source_entity is not None and alert.source_entity.type == "prism_central_vm":
        context["vm_type"] = PRISM_CENTRAL_VM
    return context


def parse_prism_alerts_v2(string_table: StringTable) -> Section:
    return [
        _alert(
            _context(alert),
            alert.message,
            (alert.creation_time - _EPOCH) // timedelta(microseconds=1),
            _SEVERITIES.get(alert.severity, alert.severity),
        )
        for alert in Alerts.model_validate_json(string_table[0][0]).root
    ]


agent_section_prism_alerts_v2 = AgentSection(
    name="prism_alerts_v2",
    parsed_section_name="prism_alerts",
    parse_function=parse_prism_alerts_v2,
)


def severity(name: str) -> tuple[int, int]:
    # first value is for sorting second is the nagios status codes
    return {
        "kInfo": (0, 0),
        "kWarning": (1, 1),
        "kCritical": (3, 2),
    }.get(name, (2, 3))


def to_string(timestamp: str) -> str:
    """Turn a textual timestamp in microseconds into a readable format"""
    return render.datetime(int(timestamp) / 1000000.0)


def check_prism_alerts(params: Params, section: Section) -> CheckResult:
    valid_alerts = (
        [e for e in section if e.get("vm_type") == PRISM_CENTRAL_VM]
        if params.get("prism_central_only")
        else section
    )

    if not valid_alerts:
        yield Result(state=State.OK, summary="No alerts")
        return

    valid_alerts = sorted(valid_alerts, key=lambda d: d["timestamp"], reverse=True)
    # find the newest alert among those with the highest severity
    immediate_alert = max(valid_alerts, key=lambda x: (severity(x["severity"])[0], x["timestamp"]))

    yield Result(
        state=State(severity(immediate_alert["severity"])[1]),
        summary="%d alerts" % len(valid_alerts),
    )

    message = immediate_alert["message"]
    state = 1 if "has the following problems" in message else 0  # see werk #7203
    yield Result(
        state=State(state),
        summary=f"Last worst on {to_string(immediate_alert['timestamp'])}: '{message}'",
    )

    yield Result(state=State.OK, notice="\nLast 10 Alerts\n")
    for i in valid_alerts[:10]:
        yield Result(state=State.OK, notice=f"{to_string(i['timestamp'])}\t{i['message']}")


check_plugin_prism_alerts = CheckPlugin(
    name="prism_alerts",
    service_name="NTNX Alerts",
    # We cannot guess items from alerts, since an empty list of alerts does not mean there are
    # no items to monitor.
    discovery_function=discover_one_service,
    check_function=check_prism_alerts,
    check_ruleset_name="prism_alerts",
    check_default_parameters={
        "prism_central_only": False,
    },
)
