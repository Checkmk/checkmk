#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable
from typing import Dict

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import AWSRegions
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.aws import GenericAWSSection, parse_aws


def discover_aws_wafv2_summary(section: GenericAWSSection) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_aws_wafv2_summary(item, params, parsed):
    web_acls_by_region: Dict[str, Dict] = {}

    for web_acl in parsed:
        try:
            region_key = AWSRegions[web_acl["Region"]]
        except KeyError:
            region_key = web_acl["Region"]  # CloudFront
        web_acls_by_region.setdefault(region_key, {})[web_acl["Name"]] = web_acl

    regions_sorted = sorted(web_acls_by_region.keys())
    long_output = []

    yield 0, "Total number of Web ACLs: %s" % len(parsed)

    for region in regions_sorted:
        web_acls_region = web_acls_by_region[region]
        yield 0, "%s: %s" % (region, len(web_acls_region))

        web_acl_names_sorted = sorted(web_acls_region.keys())
        long_output.append("%s:" % region)

        for web_acl_name in web_acl_names_sorted:
            web_acl = web_acls_region[web_acl_name]

            description = web_acl["Description"]
            if not description:
                description = "[no description]"

            long_output.append(
                "%s -- Description: %s, Number of rules and rule groups: %s"
                % (web_acl_name, description, len(web_acl["Rules"]))
            )

    if long_output:
        yield 0, "\n%s" % "\n".join(long_output)


check_info["aws_wafv2_summary"] = LegacyCheckDefinition(
    parse_function=parse_aws,
    service_name="AWS/WAFV2 Summary",
    discovery_function=discover_aws_wafv2_summary,
    check_function=check_aws_wafv2_summary,
)
