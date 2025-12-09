#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from datetime import datetime, UTC
from typing import Literal, TypedDict

from pydantic import BaseModel

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.azure_v2.agent_based.lib import parse_azure_datetime

THIRTY_DAYS = 30 * 24 * 60 * 60
SEVEN_DAYS = 7 * 24 * 60 * 60


class Params(TypedDict):
    expiration_time_secrets: FixedLevelsT[float]
    expiration_time_certificates: FixedLevelsT[float]


DEFAULT_PARAMS = Params(
    expiration_time_secrets=("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
    expiration_time_certificates=("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
)


class Credential(BaseModel):
    appId: str
    appName: str
    endDateTime: str
    keyId: str
    customKeyIdentifier: str | None = None
    displayName: str | None = None


CredentialSection = Mapping[str, Credential]


class Section(BaseModel):
    secrets: CredentialSection
    certificates: CredentialSection


def _make_credential_name(app_name: str, credential: Credential) -> str:
    identifier = credential.displayName or credential.customKeyIdentifier
    return (
        f"{app_name} - {identifier}-{credential.keyId[-8:]}"
        if identifier
        else f"{app_name} - {credential.keyId[-8:]}"
    )


def parse_app_registration(string_table: StringTable) -> Section:
    secrets = {}
    certificates = {}

    for line in string_table:
        app = json.loads(line[0])

        for cred_data in app.get("passwordCredentials", []):
            credential = Credential(
                appId=app["appId"],
                appName=app["displayName"],
                **cred_data,
            )
            secrets[_make_credential_name(app["displayName"], credential)] = credential

        for cred_data in app.get("keyCredentials", []):
            credential = Credential(
                appId=app["appId"],
                appName=app["displayName"],
                **cred_data,
            )
            certificates[_make_credential_name(app["displayName"], credential)] = credential

    return Section(secrets=secrets, certificates=certificates)


agent_section_azure_app_registration = AgentSection(
    name="azure_v2_app_registration",
    parse_function=parse_app_registration,
)


def discover_secrets(section: Section) -> DiscoveryResult:
    for key in section.secrets:
        yield Service(item=key)


def discover_certificates(section: Section) -> DiscoveryResult:
    for key in section.certificates:
        yield Service(item=key)


def _check_credential_expiration(
    credential: Credential,
    params: FixedLevelsT[float],
    credential_type: Literal["Secret", "Certificate"],
) -> CheckResult:
    expiration_date = parse_azure_datetime(credential.endDateTime)
    age = expiration_date.timestamp() - datetime.now(tz=UTC).timestamp()

    if age < 0:
        yield Result(
            state=State.CRIT,
            summary=f"{credential_type} expired: {render.timespan(abs(age))} ago",
        )
    else:
        yield from check_levels(
            age,
            levels_lower=params,
            label="Remaining time",
            render_func=render.timespan,
        )


def check_app_registration_secret(item: str, params: Params, section: Section) -> CheckResult:
    if (credential := section.secrets.get(item)) is None:
        return
    yield from _check_credential_expiration(
        credential,
        params["expiration_time_secrets"],
        credential_type="Secret",
    )


def check_app_registration_certificate(item: str, params: Params, section: Section) -> CheckResult:
    if (credential := section.certificates.get(item)) is None:
        return
    yield from _check_credential_expiration(
        credential,
        params["expiration_time_certificates"],
        credential_type="Certificate",
    )


check_plugin_azure_app_registration = CheckPlugin(
    name="azure_v2_app_registration",
    service_name="Azure/App Registration Secret %s",
    discovery_function=discover_secrets,
    check_function=check_app_registration_secret,
    check_ruleset_name="azure_v2_app_registration",
    check_default_parameters=DEFAULT_PARAMS,
)

check_plugin_azure_app_registration_certificates = CheckPlugin(
    name="azure_v2_app_registration_certificates",
    sections=["azure_v2_app_registration"],
    service_name="Azure/App Registration Certificate %s",
    discovery_function=discover_certificates,
    check_function=check_app_registration_certificate,
    check_ruleset_name="azure_v2_app_registration",
    check_default_parameters=DEFAULT_PARAMS,
)
