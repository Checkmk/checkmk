#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from datetime import datetime, timezone

from pydantic import BaseModel

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.azure import parse_azure_datetime

THIRTY_DAYS = 30 * 24 * 60 * 60
SEVEN_DAYS = 7 * 24 * 60 * 60


class ClientSecret(BaseModel):
    appId: str
    appName: str
    endDateTime: str
    keyId: str
    customKeyIdentifier: str | None = None
    displayName: str | None = None


Section = Mapping[str, ClientSecret]


def parse_app_registration(string_table: StringTable) -> Section:
    section = {}
    for line in string_table:
        app = json.loads(line[0])
        for credentials in app.get("passwordCredentials", []):
            secret = ClientSecret(appId=app["appId"], appName=app["displayName"], **credentials)
            secret_name = (
                f"{secret.appName} - {secret.displayName}"
                if secret.displayName
                else f"{secret.appName} - {secret.customKeyIdentifier}"
            )
            section[secret_name] = secret

    return section


register.agent_section(
    name="azure_app_registration",
    parse_function=parse_app_registration,
)


def discover_app_registration(section: Section) -> DiscoveryResult:
    for key in section:
        yield Service(item=key)


def check_app_registration(
    item: str, params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    if (secret := section.get(item)) is None:
        return

    expiration_date = parse_azure_datetime(secret.endDateTime)
    age = expiration_date.timestamp() - datetime.now(tz=timezone.utc).timestamp()

    if age < 0:
        yield Result(
            state=State.CRIT,
            summary=f"Secret expired: {render.timespan(abs(age))} ago",
        )

    else:
        yield from check_levels(
            age,
            levels_lower=params.get("expiration_time"),
            label="Remaining time",
            render_func=render.timespan,
        )


register.check_plugin(
    name="azure_app_registration",
    service_name="Azure/App Registration Secret %s",
    discovery_function=discover_app_registration,
    check_function=check_app_registration,
    check_ruleset_name="credentials_expiration",
    check_default_parameters={"expiration_time": (THIRTY_DAYS, SEVEN_DAYS)},
)
