#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

# Pydantic requires the property to be under computed_field to work.
# mypy: disable-error-code="prop-decorator"

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping

from pydantic import BaseModel, computed_field

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

type Section = Mapping[str, ResponseCodes]


class ResponseCodeCount(BaseModel, frozen=True):
    code: int
    count: int


class ResponseCodes(BaseModel, frozen=True):
    organization_id: str
    organization_name: str
    counts: list[ResponseCodeCount]

    @computed_field
    @property
    def identifier(self) -> str:
        return f"{self.organization_name}/{self.organization_id}"


def parse_api_response_codes(string_table: StringTable) -> Section:
    match string_table:
        case [[payload]] if payload:
            response_codes = (ResponseCodes.model_validate(item) for item in json.loads(payload))
            return {info.identifier: info for info in response_codes}
        case _:
            return {}


agent_section_cisco_meraki_org_api_response_codes = AgentSection(
    name="cisco_meraki_org_api_response_codes",
    parsed_section_name="cisco_meraki_org_api_response_codes",
    parse_function=parse_api_response_codes,
)


def discover_api_response_codes(section: Section) -> DiscoveryResult:
    for identifier in section:
        yield Service(item=identifier)


def check_response_code_count_levels(value: int | None, *, code: int) -> Iterable[Result | Metric]:
    if not value:
        return []

    return check_levels(
        value=value,
        label=f"Code {code}xx",
        render_func=lambda v: str(v),
        metric_name=f"api_code_{code}xx",
        notice_only=False,
    )


def check_api_response_codes(item: str, section: Section) -> CheckResult:
    if (info := section.get(item)) is None:
        return

    yield Result(state=State.OK, notice=f"Organization name: {info.organization_name}")
    yield Result(state=State.OK, notice=f"Organization ID: {info.organization_id}")

    counter: dict[int, int] = defaultdict(int)

    for status in info.counts:
        response_class = status.code // 100  # e.g. 404 => 4
        counter[response_class] += status.count

    yield from check_response_code_count_levels(counter.get(2), code=2)  # 2xx code
    yield from check_response_code_count_levels(counter.get(3), code=3)  # 3xx code
    yield from check_response_code_count_levels(counter.get(4), code=4)  # 4xx code
    yield from check_response_code_count_levels(counter.get(5), code=5)  # 5xx code


check_plugin_cisco_meraki_org_api_response_codes = CheckPlugin(
    name="cisco_meraki_org_api_response_codes",
    sections=["cisco_meraki_org_api_response_codes"],
    service_name="API %s",
    discovery_function=discover_api_response_codes,
    check_function=check_api_response_codes,
)
