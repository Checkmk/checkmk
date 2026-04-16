#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.aws.constants import AWS_REGIONS
from cmk.plugins.aws.lib import GenericAWSSection, parse_aws

_REGIONS: Mapping[str, str] = dict(AWS_REGIONS)


def discover_aws_wafv2_summary(section: GenericAWSSection) -> DiscoveryResult:
    if section:
        yield Service()


def check_aws_wafv2_summary(section: GenericAWSSection) -> CheckResult:
    web_acls_by_region: dict[str, dict[str, dict[str, Any]]] = {}

    for web_acl in section:
        try:
            region_key = _REGIONS[web_acl["Region"]]
        except KeyError:
            region_key = web_acl["Region"]  # CloudFront
        web_acls_by_region.setdefault(region_key, {})[web_acl["Name"]] = web_acl

    regions_sorted = sorted(web_acls_by_region.keys())
    long_output = []

    yield Result(state=State.OK, summary=f"Total number of Web ACLs: {len(section)}")

    for region in regions_sorted:
        web_acls_region = web_acls_by_region[region]
        yield Result(state=State.OK, summary=f"{region}: {len(web_acls_region)}")

        web_acl_names_sorted = sorted(web_acls_region.keys())
        long_output.append(f"{region}:")

        for web_acl_name in web_acl_names_sorted:
            web_acl = web_acls_region[web_acl_name]

            description = web_acl["Description"]
            if not description:
                description = "[no description]"

            long_output.append(
                f"{web_acl_name} -- Description: {description},"
                f" Number of rules and rule groups: {len(web_acl['Rules'])}"
            )

    if long_output:
        # Reproduces the legacy convert_legacy_results summary text for an output
        # starting with "\n" (i.e. "details only"). The user-visible service summary
        # kept this text in the legacy plug-in, so we keep it here to avoid a
        # behaviour change.
        detail_count = len(long_output)
        yield Result(
            state=State.OK,
            summary=f"{detail_count} additional detail{'' if detail_count == 1 else 's'} available",
            details="\n".join(long_output),
        )


agent_section_aws_wafv2_summary = AgentSection(
    name="aws_wafv2_summary",
    parse_function=parse_aws,
)


check_plugin_aws_wafv2_summary = CheckPlugin(
    name="aws_wafv2_summary",
    service_name="AWS/WAFV2 Summary",
    discovery_function=discover_aws_wafv2_summary,
    check_function=check_aws_wafv2_summary,
)
