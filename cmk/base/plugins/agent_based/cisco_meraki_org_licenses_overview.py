#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.cisco_meraki import load_json, MerakiAPIData


@dataclass(frozen=True)
class LicensesOverview:
    status: str
    expiration_date: datetime | None
    licensed_device_counts: Mapping[str, int]

    @classmethod
    def parse(cls, row: MerakiAPIData) -> "LicensesOverview":
        return cls(
            status=str(row["status"]),
            expiration_date=cls._parse_expiration_date(str(row["expirationDate"])),
            licensed_device_counts=(
                counts if isinstance(counts := row["licensedDeviceCounts"], dict) else {}
            ),
        )

    @staticmethod
    def _parse_expiration_date(raw_expiration_date: str) -> datetime | None:
        try:
            return datetime.strptime(raw_expiration_date, "%b %d, %Y %Z")
        except ValueError:
            return None


Section = Mapping[str, LicensesOverview]


def parse_licenses_overview(string_table: StringTable) -> Section:
    def _make_item_name(row: Mapping[str, object]) -> str:
        # Not sure if the 'name' is always available and/or unique
        if "name" in row:
            return f"{row['name']}/{row['id']}"
        return f"{row['id']}"

    return {_make_item_name(row): LicensesOverview.parse(row) for row in load_json(string_table)}


register.agent_section(
    name="cisco_meraki_org_licenses_overview",
    parse_function=parse_licenses_overview,
)


def discover_licenses_overview(section: Section) -> DiscoveryResult:
    for organisation_id in section:
        yield Service(item=organisation_id)


def check_licenses_overview(
    item: str,
    params: Mapping[str, tuple[int, int]],
    section: Section,
) -> CheckResult:
    if (item_data := section.get(item)) is None:
        return

    yield Result(
        state=State.OK if item_data.status == "OK" else State.WARN,
        summary=f"Status: {item_data.status}",
    )

    if item_data.expiration_date is not None:
        yield from _check_expiration_date(item_data.expiration_date, params)

    if item_data.licensed_device_counts:
        yield Result(
            state=State.OK,
            summary=f"Number of licensed devices: {sum(item_data.licensed_device_counts.values())}",
        )

    for device_type, device_count in sorted(
        item_data.licensed_device_counts.items(),
        key=lambda t: t[0],
    ):
        yield Result(state=State.OK, notice=f"{device_type}: {device_count} licensed devices")


def _check_expiration_date(
    expiration_date: datetime,
    params: Mapping[str, tuple[int, int]],
) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"Expiration date: {expiration_date.strftime('%b %d, %Y')}",
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
            levels_lower=params.get("remaining_expiration_time"),
            label="Remaining time",
            render_func=render.timespan,
        )


register.check_plugin(
    name="cisco_meraki_org_licenses_overview",
    service_name="Cisco Meraki Organisation %s Licenses Overview",
    discovery_function=discover_licenses_overview,
    check_function=check_licenses_overview,
    check_ruleset_name="cisco_meraki_org_licenses_overview",
    check_default_parameters={},
)
