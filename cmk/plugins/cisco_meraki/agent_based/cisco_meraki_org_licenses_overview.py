#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Pydantic requires the property to be under computed_field to work.
# mypy: disable-error-code="prop-decorator"

# Unpacking literal keys into dictionary with str keys is a known mypy bug:
# https://github.com/python/mypy/issues/19893
# mypy: disable-error-code="dict-item"

import json
import time
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime
from typing import Literal, TypedDict

from pydantic import BaseModel, computed_field, Field

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel

type Section = Mapping[str, LicensesOverview]

type LicenseCountsByDeviceType = defaultdict[
    Literal[
        "gateway_mg_count",
        "security_mx_count",
        "switch_ms_count",
        "video_mv_count",
        "sensor_mt_count",
        "wireless_mr_count",
        "systems_manager_sm_count",
        "other_count",
    ],
    int,
]


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

    def get_device_counts_by_type(self) -> LicenseCountsByDeviceType:
        counts_by_type: LicenseCountsByDeviceType = defaultdict(int)

        for serial, count in self.licensed_device_counts.items():
            serial_ = serial.lower()
            if serial_.startswith("mg"):
                counts_by_type["gateway_mg_count"] += count
            elif serial_.startswith("mx"):
                counts_by_type["security_mx_count"] += count
            elif serial_.startswith("ms"):
                counts_by_type["switch_ms_count"] += count
            elif serial_.startswith("mv"):
                counts_by_type["video_mv_count"] += count
            elif serial_.startswith("mt"):
                counts_by_type["sensor_mt_count"] += count
            elif serial_.startswith("mr") or serial.startswith("wireless"):
                counts_by_type["wireless_mr_count"] += count
            elif serial_.startswith("sm"):
                counts_by_type["systems_manager_sm_count"] += count
            else:
                counts_by_type["other_count"] += count

        return counts_by_type


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
    state_license_not_ok: int


def check_licenses_overview(item: str, params: CheckParams, section: Section) -> CheckResult:
    if (overview := section.get(item)) is None:
        return

    yield Result(state=State.OK, notice=f"Organization ID: {overview.organisation_id}")
    yield Result(state=State.OK, notice=f"Organization name: {overview.organisation_name}")

    yield Result(
        state=State.OK if overview.status == "OK" else State(params["state_license_not_ok"]),
        summary=f"Status: {overview.status}",
    )

    if overview.expiration_date is not None:
        yield from _check_expiration_date(overview.expiration_date, params)

    if overview.licensed_device_counts:
        yield Result(
            state=State.OK,
            summary=f"Number of licensed devices: {overview.license_total}",
        )
        yield Metric("license_total", overview.license_total)

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
        yield Metric("remaining_time", 0)
    else:
        yield from check_levels(
            age,
            levels_lower=params["remaining_expiration_time"],
            label="Remaining time",
            render_func=render.timespan,
        )
        # NOTE: opting to not use the `metric_name` parameter in check levels call above because
        # then the lower levels will not be displayed in the graph. Once that is supported, we can
        # drop the line below and add the metric name directly to check levels.
        yield Metric("remaining_time", age, levels=params["remaining_expiration_time"][1])


check_plugin_cisco_meraki_org_licenses_overview = CheckPlugin(
    name="cisco_meraki_org_licenses_overview",
    service_name="Cisco Meraki Licenses %s",
    discovery_function=discover_licenses_overview,
    check_function=check_licenses_overview,
    check_ruleset_name="cisco_meraki_org_licenses_overview",
    check_default_parameters=CheckParams(
        remaining_expiration_time=("no_levels", None),
        state_license_not_ok=State.WARN.value,
    ),
)


def inventorize_licenses_overview(section: Section) -> InventoryResult:
    path = ["software", "applications", "cisco_meraki", "licenses"]
    for overview in section.values():
        yield TableRow(
            path=path,
            key_columns={
                "org_id": overview.organisation_id,
            },
            inventory_columns={
                "org_name": overview.organisation_name,
                "summary": overview.license_total,
                **overview.get_device_counts_by_type(),
            },
        )


inventory_plugin_cisco_meraki_org_licenses_overview = InventoryPlugin(
    name="cisco_meraki_org_licenses_overview",
    inventory_function=inventorize_licenses_overview,
    sections=["cisco_meraki_org_licenses_overview"],
)
