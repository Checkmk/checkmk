#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.veeam.lib import parse_iso8601_epoch

_DAY = 60.0 * 60.0 * 24.0


@dataclass(frozen=True, kw_only=True)
class VeeamLicense:
    """Mirrors the VBR REST API's LicenseModel (GET /api/v1/license)."""

    status: str
    edition: str
    type: str | None
    expiration_date: float | None
    support_expiration_date: float | None
    licensed_to: str
    auto_update_enabled: bool
    instances_licensed: int | None
    instances_used: int | None
    sockets_licensed: int | None
    sockets_used: int | None
    capacity_licensed_tb: float | None
    capacity_used_tb: float | None


Section = VeeamLicense


class CheckParameters(TypedDict):
    license_expiry: LevelsT[float]
    support_expiry: LevelsT[float]
    consumption: LevelsT[float]


def parse_veeam_license(string_table: StringTable) -> Section:
    license_dict = json.loads(string_table[0][0])
    instances = license_dict.get("instanceLicenseSummary") or {}
    sockets = license_dict.get("socketLicenseSummary") or {}
    capacity = license_dict.get("capacityLicenseSummary") or {}
    expiration_date = license_dict.get("expirationDate")
    support_expiration_date = license_dict.get("supportExpirationDate")
    return VeeamLicense(
        status=license_dict["status"],
        edition=license_dict["edition"],
        type=license_dict.get("type"),
        expiration_date=(
            parse_iso8601_epoch(expiration_date) if expiration_date is not None else None
        ),
        support_expiration_date=(
            parse_iso8601_epoch(support_expiration_date)
            if support_expiration_date is not None
            else None
        ),
        licensed_to=license_dict["licensedTo"],
        auto_update_enabled=license_dict["autoUpdateEnabled"],
        instances_licensed=instances.get("licensedInstancesNumber"),
        instances_used=instances.get("usedInstancesNumber"),
        sockets_licensed=sockets.get("licensedSocketsNumber"),
        sockets_used=sockets.get("usedSocketsNumber"),
        capacity_licensed_tb=capacity.get("licensedCapacityTb"),
        capacity_used_tb=capacity.get("usedCapacityTb"),
    )


def discovery_veeam_license(section: Section) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def monitoring_state(status: str) -> State:
    match status:
        case "Valid":
            return State.OK
        case "Invalid" | "Expired":
            return State.CRIT
        case _:
            return State.UNKNOWN


def _check_expiry(
    label: str,
    metric_name: str,
    expiry: float | None,
    levels: LevelsT[float],
    now: float,
) -> CheckResult:
    if expiry is None:
        return
    remaining = expiry - now
    yield from check_levels(
        remaining,
        levels_lower=levels,
        metric_name=metric_name,
        render_func=lambda v: (
            render.timespan(v) if v >= 0 else f"expired {render.timespan(-v)} ago"
        ),
        label=label,
    )


def _check_consumption(
    label: str,
    metric_name: str,
    licensed: float | None,
    used: float | None,
    levels: LevelsT[float],
) -> CheckResult:
    if licensed is None or used is None or licensed <= 0:
        return
    yield from check_levels(
        used / licensed * 100.0,
        levels_upper=levels,
        metric_name=metric_name,
        render_func=render.percent,
        label=label,
    )


def check_veeam_license(params: CheckParameters, section: Section) -> CheckResult:
    yield Result(
        state=monitoring_state(section.status),
        summary=f"{section.edition}, {section.status}",
    )

    yield Result(state=State.OK, summary=f"Licensed to: {section.licensed_to}")
    if section.type is not None:
        yield Result(state=State.OK, summary=f"Type: {section.type}")
    yield Result(
        state=State.OK,
        summary=f"Auto update: {'enabled' if section.auto_update_enabled else 'disabled'}",
    )

    now = time.time()
    yield from _check_expiry(
        "License expiry",
        "veeam_license_expiry",
        section.expiration_date,
        params["license_expiry"],
        now,
    )
    yield from _check_expiry(
        "Support expiry",
        "veeam_license_support_expiry",
        section.support_expiration_date,
        params["support_expiry"],
        now,
    )

    # Mutually exclusive by license type: exactly one of these is populated.
    yield from _check_consumption(
        "Instances used",
        "veeam_license_instances_percent",
        section.instances_licensed,
        section.instances_used,
        params["consumption"],
    )
    yield from _check_consumption(
        "Sockets used",
        "veeam_license_sockets_percent",
        section.sockets_licensed,
        section.sockets_used,
        params["consumption"],
    )
    yield from _check_consumption(
        "Capacity used",
        "veeam_license_capacity_percent",
        section.capacity_licensed_tb,
        section.capacity_used_tb,
        params["consumption"],
    )


agent_section_veeam_license = AgentSection(
    name="veeam_license",
    parse_function=parse_veeam_license,
)

check_plugin_veeam_license = CheckPlugin(
    name="veeam_license",
    service_name="Veeam License",
    discovery_function=discovery_veeam_license,
    check_function=check_veeam_license,
    check_ruleset_name="veeam_license",
    # TODO: proposed defaults, unvalidated against a real VBR instance. Revisit
    # once real license expiry/consumption data is available.
    check_default_parameters=CheckParameters(
        license_expiry=("fixed", (30 * _DAY, 7 * _DAY)),
        support_expiry=("fixed", (30 * _DAY, 7 * _DAY)),
        consumption=("fixed", (80.0, 95.0)),
    ),
)
