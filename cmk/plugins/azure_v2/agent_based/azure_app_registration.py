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
    LevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.azure_v2.agent_based.lib import parse_azure_datetime

THIRTY_DAYS = 30 * 24 * 60 * 60.0
SEVEN_DAYS = 7 * 24 * 60 * 60.0
SIX_MONTHS_ONE_DAY = 181 * 24 * 60 * 60.0


class _CredentialParams(TypedDict, total=False):
    remaining_validity: LevelsT[float]
    max_validity: LevelsT[float]
    ignore_if_older_than: float


class Params(TypedDict, total=False):
    secrets: _CredentialParams
    certificates: _CredentialParams


DEFAULT_PARAMS = Params(
    secrets=_CredentialParams(
        remaining_validity=("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
        max_validity=("fixed", (SIX_MONTHS_ONE_DAY, SIX_MONTHS_ONE_DAY)),
    ),
    certificates=_CredentialParams(
        remaining_validity=("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
        max_validity=("fixed", (SIX_MONTHS_ONE_DAY, SIX_MONTHS_ONE_DAY)),
    ),
)


class Credential(BaseModel):
    appId: str
    appName: str
    startDateTime: str | None = None
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
    remaining_validity: LevelsT[float] | None,
    max_validity: LevelsT[float] | None,
    credential_type: Literal["Secret", "Certificate"],
    ignore_if_older_than: float | None = None,
) -> CheckResult:
    start_date = (
        parse_azure_datetime(credential.startDateTime)
        if credential.startDateTime is not None  # None with old agents output
        else None
    )

    expiration_date = parse_azure_datetime(credential.endDateTime)
    age = expiration_date.timestamp() - datetime.now(tz=UTC).timestamp()
    if age < 0:
        if ignore_if_older_than is not None:
            if abs(age) > ignore_if_older_than:
                yield Result(
                    state=State.OK,
                    summary=f"{credential_type} ignored: expired more than {render.timespan(ignore_if_older_than)} ago",
                )
                return

        yield Result(
            state=State.CRIT,
            summary=f"{credential_type} expired: {render.timespan(abs(age))} ago",
        )
        return
    elif remaining_validity is not None:
        yield from check_levels(
            age,
            levels_lower=remaining_validity,
            label="Remaining time",
            render_func=render.timespan,
        )
    else:
        yield Result(state=State.OK, summary=f"Remaining time: {render.timespan(age)}")

    if max_validity is not None and start_date is not None and max_validity[0] != "no_levels":
        total_validity = expiration_date.timestamp() - start_date.timestamp()
        yield from check_levels(
            total_validity,
            levels_upper=max_validity,
            label="Max validity",
            render_func=render.timespan,
        )


def check_app_registration_secret(item: str, params: Params, section: Section) -> CheckResult:
    if (credential := section.secrets.get(item)) is None:
        return
    cred_params = params.get("secrets", {})
    yield from _check_credential_expiration(
        credential,
        remaining_validity=cred_params.get("remaining_validity"),
        max_validity=cred_params.get("max_validity"),
        credential_type="Secret",
        ignore_if_older_than=cred_params.get("ignore_if_older_than"),
    )


def check_app_registration_certificate(item: str, params: Params, section: Section) -> CheckResult:
    if (credential := section.certificates.get(item)) is None:
        return
    cred_params = params.get("certificates", {})
    yield from _check_credential_expiration(
        credential,
        remaining_validity=cred_params.get("remaining_validity"),
        max_validity=cred_params.get("max_validity"),
        credential_type="Certificate",
        ignore_if_older_than=cred_params.get("ignore_if_older_than"),
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
