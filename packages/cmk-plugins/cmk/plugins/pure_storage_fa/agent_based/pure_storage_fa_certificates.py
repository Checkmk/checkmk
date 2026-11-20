#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional


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


class Certificate(BaseModel, frozen=True):
    name: Optional[str] = None
    status: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    certificate_type: Optional[str] = None
    intermediate_certificate: Optional[str] = None
    email: Optional[str] = None
    subject_alternative_names: Optional[list] = None
    common_name: Optional[str] = None
    organization: Optional[str] = None
    organizational_unit: Optional[str] = None
    locality: Optional[str] = None
    key_algorithm: Optional[str] = None
    key_size: Optional[int] = None
    issued_by: Optional[str] = None
    issued_to: Optional[str] = None
    valid_from: Optional[int] = None
    valid_to: Optional[int] = None


def parse_certificates(string_table: StringTable) -> list[Certificate]:
    json_data = json.loads(string_table[0][0])
    if "items" not in json_data:
        return None
    parsed = []
    for cert in json_data["items"]:
        parsed.append(Certificate(**cert))

    return parsed


agent_section_pure_storage_fa_certificates = AgentSection(
    name="pure_storage_fa_certificates",
    parse_function=parse_certificates,
)


def discover_certificates(section: list[Certificate]) -> DiscoveryResult:
    for cert in section:
        yield Service(item=cert.name)


def check_certificates(item, section: list[Certificate]) -> CheckResult:
    for certificate in section:
        if item == certificate.name:
            now = datetime.now(timezone.utc)
            valid_to = datetime.fromtimestamp(
                certificate.valid_to / 1000, tz=timezone.utc
            )

            if valid_to < now:
                yield Result(state=State.CRIT, summary="Certificate ran out")
            else:
                yield Result(
                    state=State.OK,
                    summary=f"{certificate.status} certificate valid until {valid_to.strftime('%d.%m.%Y')}",
                )


check_plugin_pure_storage_fa_certificates = CheckPlugin(
    name="pure_storage_fa_certificates",
    service_name="PureStorage Certificate Status %s",
    discovery_function=discover_certificates,
    check_function=check_certificates,
)
