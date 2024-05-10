#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator, Mapping, Sequence
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    replace_macros,
)

_DAY: Final[int] = 24 * 3600
_MILLISECOND: Final[int] = 1000


class LevelsType(StrEnum):
    NO_LEVELS = "no_levels"
    FIXED = "fixed"


class ServicePrefix(StrEnum):
    AUTO = "auto"
    NONE = "none"


FloatLevels = (
    tuple[Literal[LevelsType.NO_LEVELS], None]
    | tuple[Literal[LevelsType.FIXED], tuple[float, float]]
)

SignatureAlgorithm = tuple[str, str]

PubKey = tuple[str, str]


class ServiceDescription(BaseModel):
    prefix: ServicePrefix
    name: str


class Issuer(BaseModel):
    common_name: str | None = None
    organization: str | None = None
    org_unit: str | None = None
    state: str | None = None
    country: str | None = None


class Subject(BaseModel):
    common_name: str | None = None
    organization: str | None = None
    org_unit: str | None = None
    pubkey_algorithm: PubKey | None = None
    pubkey_size: str | None = None


class Certificate(BaseModel):
    remaining: FloatLevels | None = None
    maximum: float | None = None
    self_signed: bool


class CertificateDetails(BaseModel):
    serialnumber: str | None = None
    signature_algorithm: SignatureAlgorithm | None = None
    issuer: Issuer | None = None
    subject: Subject | None = None
    altnames: list[str] | None = None


class Settings(BaseModel):
    response_time: FloatLevels | None = None
    validity: Certificate | None = None
    cert_details: CertificateDetails | None = None


class StandardSettings(Settings):
    port: int


class CertEndpoint(BaseModel):
    service_name: ServiceDescription
    address: str
    port: int | None = None
    individual_settings: Settings | None = None


class RawParams(BaseModel):
    connections: list[CertEndpoint]
    standard_settings: StandardSettings


def parse_cert_params(raw_params: Mapping[str, object]) -> Sequence[CertEndpoint]:
    params = RawParams.model_validate(raw_params)
    return [
        CertEndpoint(
            service_name=connection.service_name,
            address=connection.address,
            port=connection.port if connection.port else params.standard_settings.port,
            individual_settings=_merge_settings(
                params.standard_settings, connection.individual_settings
            ),
        )
        for connection in params.connections
    ]


def _merge_settings(standard: StandardSettings, individual: Settings | None) -> Settings | None:
    if individual is None:
        return standard

    return Settings.model_validate(
        standard.model_dump(exclude_none=True) | individual.model_dump(exclude_none=True)
    )


def generate_cert_services(
    params: Sequence[CertEndpoint], host_config: HostConfig
) -> Iterator[ActiveCheckCommand]:
    macros = host_config.macros
    for endpoint in params:
        prefix = "CERT " if endpoint.service_name.prefix is ServicePrefix.AUTO else ""
        endpoint.address = replace_macros(endpoint.address, macros)
        yield ActiveCheckCommand(
            service_description=f"{prefix}{replace_macros(endpoint.service_name.name, macros)}",
            command_arguments=list(_command_arguments(endpoint)),
        )


def _command_arguments(endpoint: CertEndpoint) -> Iterator[str]:
    yield "--url"
    yield endpoint.address

    if (port := endpoint.port) is not None:
        yield "--port"
        yield str(port)

    if (settings := endpoint.individual_settings) is None:
        return

    if (response_time := settings.response_time) is not None:
        yield from _response_time_args(response_time)
    if (validity := settings.validity) is not None:
        yield from _validity_args(validity)
    if (cert_details := settings.cert_details) is not None:
        yield from _cert_details_args(cert_details)


def _response_time_args(response_time: FloatLevels) -> Iterator[str]:
    match response_time:
        case (LevelsType.FIXED, (float(warn), float(crit))):
            yield "--response-time"
            yield f"{int(warn * _MILLISECOND)}"
            yield f"{int(crit * _MILLISECOND)}"


def _validity_args(validity: Certificate) -> Iterator[str]:
    if (remaining := validity.remaining) is not None:
        yield from _remaining_args(remaining)
    if (maximum := validity.maximum) is not None:
        yield "--max-validity"
        yield f"{round(maximum / _DAY)}"
    if validity.self_signed:
        yield "--allow-self-signed"


def _remaining_args(remaining: FloatLevels) -> Iterator[str]:
    match remaining:
        case (LevelsType.FIXED, (float(warn), float(crit))):
            yield "--not-after"
            yield f"{round(warn / _DAY)}"
            yield f"{round(crit / _DAY)}"


def _cert_details_args(cert_details: CertificateDetails) -> Iterator[str]:
    if (serialnumber := cert_details.serialnumber) is not None:
        yield "--serial"
        yield serialnumber
    if (signature_algorithm := cert_details.signature_algorithm) is not None:
        yield from _signature_algorithm_args(signature_algorithm)
    if (issuer := cert_details.issuer) is not None:
        yield from _issuer_args(issuer)
    if (subject := cert_details.subject) is not None:
        yield from _subject_args(subject)
    if (alt_names := cert_details.altnames) is not None:
        for alt_name in alt_names:
            yield "--subject-alt-names"
            yield alt_name


def _signature_algorithm_args(signature_algorithm: SignatureAlgorithm) -> Iterator[str]:
    encryption_algorithm = signature_algorithm[1]
    yield "--signature-algorithm"
    yield encryption_algorithm


def _issuer_args(issuer: Issuer) -> Iterator[str]:
    if (common_name := issuer.common_name) is not None:
        yield "--issuer-cn"
        yield common_name
    if (org := issuer.organization) is not None:
        yield "--issuer-o"
        yield org
    if (org_unit := issuer.org_unit) is not None:
        yield "--issuer-ou"
        yield org_unit
    if (state := issuer.state) is not None:
        yield "--issuer-st"
        yield state
    if (country := issuer.country) is not None:
        yield "--issuer-c"
        yield country


def _subject_args(subject: Subject) -> Iterator[str]:
    if (common_name := subject.common_name) is not None:
        yield "--subject-cn"
        yield common_name
    if (org := subject.organization) is not None:
        yield "--subject-o"
        yield org
    if (org_unit := subject.org_unit) is not None:
        yield "--subject-ou"
        yield org_unit
    if (pubkey := subject.pubkey_algorithm) is not None:
        yield "--pubkey-algorithm"
        yield pubkey[0]
    if (pubkey_size := subject.pubkey_size) is not None:
        yield "--pubkey-size"
        yield pubkey_size


active_check_cert = ActiveCheckConfig(
    name="cert",
    parameter_parser=parse_cert_params,
    commands_function=generate_cert_services,
)
