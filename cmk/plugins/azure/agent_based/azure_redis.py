#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.azure import (
    get_service_labels_from_resource_tags,
    parse_resources,
    Section,
)


# redis, general service, just to get something to show up
def discover_azure_redis(section: Section) -> DiscoveryResult:
    for item, resource in section.items():
        yield Service(item=item, labels=get_service_labels_from_resource_tags(resource.tags))


def check_azure_redis(item: str, section: Section) -> CheckResult:
    if (resource := section.get(item)) is None:
        raise IgnoreResultsError("Data not present at the moment")
    # TODO: Maybe something more than location here... but for now...
    yield Result(state=State.OK, summary=f"Location: {resource.location}")


check_plugin_azure_redis = CheckPlugin(
    name="azure_redis",
    sections=["azure_redis"],
    service_name="Redis %s",
    discovery_function=discover_azure_redis,
    check_function=check_azure_redis,
)

agent_section_azure_redis = AgentSection(name="azure_redis", parse_function=parse_resources)
