#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.aws import check_aws_elb_summary_generic
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.aws import GenericAWSSection, parse_aws


def discover_aws_elb_summary(section: GenericAWSSection) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


check_info["aws_elb_summary"] = LegacyCheckDefinition(
    parse_function=parse_aws,
    service_name="AWS/ELB Summary",
    discovery_function=discover_aws_elb_summary,
    check_function=check_aws_elb_summary_generic,
)
