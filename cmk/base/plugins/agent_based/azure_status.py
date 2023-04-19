#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

_NO_ISSUES = Result(
    state=State.OK, summary="No known issues. Details: https://azure.status.microsoft/en-us/status"
)


class AzureIssue(BaseModel, frozen=True):
    region: str
    title: str
    description: str


class AzureStatus(BaseModel, frozen=True):
    link: str
    regions: Sequence[str]
    issues: Sequence[AzureIssue]


class AzureStatusesPerRegion(BaseModel, frozen=True):
    link: str
    regions: Mapping[str, Sequence[AzureIssue]]


def parse_azure_status(string_table: StringTable) -> AzureStatusesPerRegion:
    azure_status = AzureStatus.parse_raw(string_table[0][0])

    regions: dict[str, list[AzureIssue]] = {r: [] for r in azure_status.regions}
    for issue in azure_status.issues:
        regions[issue.region].append(issue)

    return AzureStatusesPerRegion(link=azure_status.link, regions=regions)


register.agent_section(
    name="azure_status",
    parse_function=parse_azure_status,
)


def discover_azure_status(section: AzureStatusesPerRegion) -> DiscoveryResult:
    for item in section.regions.keys():
        yield Service(item=item)


def check_azure_status(item: str, section: AzureStatusesPerRegion) -> CheckResult:
    if (issues := section.regions.get(item)) is None:
        return

    if not issues:
        yield _NO_ISSUES
        return

    issue_string = "issue" if len(issues) == 1 else "issues"
    yield Result(state=State.WARN, summary=f"{len(issues)} {issue_string}: {section.link}")
    for issue in issues:
        yield Result(state=State.OK, summary=issue.title)
        yield Result(state=State.OK, notice=issue.description)


register.check_plugin(
    name="azure_status",
    service_name="Azure Status %s",
    discovery_function=discover_azure_status,
    check_function=check_azure_status,
)
