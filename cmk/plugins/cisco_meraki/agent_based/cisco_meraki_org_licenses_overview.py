#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Pydantic requires the property to be under computed_field to work.
# mypy: disable-error-code="prop-decorator"

import json
import time
from collections.abc import Mapping
from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, computed_field, Field

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel

type Section = Mapping[str, LicensesOverview]


class LicensesOverview(BaseModel, frozen=True):
    organisation_id: str
    organisation_name: str
    status: str
    raw_expiration_date: str | None = Field(alias="expirationDate")
    licensed_device_counts: dict[str, int] = Field(alias="licensedDeviceCounts")

    @computed_field
    @property
    def identifier(self) -> str:
        return f"{self.organisation_name}/{self.organisation_id}"

    @computed_field
    @property
    def expiration_date(self) -> datetime | None:
        if not self.raw_expiration_date:
            return None
        return datetime.strptime(self.raw_expiration_date, "%b %d, %Y %Z")

    @computed_field
    @property
    def license_total(self) -> int:
        return sum(self.licensed_device_counts.values())


def parse_licenses_overview(string_table: StringTable) -> Section:
    match string_table:
        case [[payload]] if payload:
            overviews = (LicensesOverview.model_validate(item) for item in json.loads(payload))
            return {overview.identifier: overview for overview in overviews}
        case _:
            return {}


agent_section_cisco_meraki_org_licenses_overview = AgentSection(
    name="cisco_meraki_org_licenses_overview",
    parse_function=parse_licenses_overview,
)


def discover_licenses_overview(section: Section) -> DiscoveryResult:
    for identifier in section:
        yield Service(item=identifier)


class CheckParams(TypedDict):
    remaining_expiration_time: SimpleLevelsConfigModel[int]


def check_licenses_overview(item: str, params: CheckParams, section: Section) -> CheckResult:
    if (overview := section.get(item)) is None:
        return

    yield Result(state=State.OK, notice=f"Organization ID: {overview.organisation_id}")
    yield Result(state=State.OK, notice=f"Organization name: {overview.organisation_name}")

    yield Result(
        state=State.OK if overview.status == "OK" else State.WARN,
        summary=f"Status: {overview.status}",
    )

    if overview.expiration_date is not None:
        yield from _check_expiration_date(overview.expiration_date, params)

    if overview.licensed_device_counts:
        yield Result(
            state=State.OK,
            summary=f"Number of licensed devices: {overview.license_total}",
        )

    for device_type, device_count in sorted(overview.licensed_device_counts.items()):
        yield Result(state=State.OK, notice=f"{device_type}: {device_count} licensed devices")


def _check_expiration_date(expiration_date: datetime, params: CheckParams) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"Expiration date: {expiration_date.date().isoformat()}",
    )

    age = expiration_date.timestamp() - time.time()

    if age < 0:
        yield Result(
            state=State.CRIT,
            summary=f"Licenses expired: {render.timespan(abs(age))} ago",
        )

    else:
        yield from check_levels(
            age,
            levels_lower=params["remaining_expiration_time"],
            label="Remaining time",
            render_func=render.timespan,
        )


check_plugin_cisco_meraki_org_licenses_overview = CheckPlugin(
    name="cisco_meraki_org_licenses_overview",
    service_name="Cisco Meraki Licenses %s",
    discovery_function=discover_licenses_overview,
    check_function=check_licenses_overview,
    check_ruleset_name="cisco_meraki_org_licenses_overview",
    check_default_parameters=CheckParams(
        remaining_expiration_time=("no_levels", None),
    ),
)
