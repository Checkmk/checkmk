#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

from cmk.base.plugins.agent_based.utils.aws import (
    AWSLimitsByRegion,
    check_aws_limits,
    parse_aws_limits_generic,
)

from .agent_based_api.v1 import register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

register.agent_section(
    name="aws_sns_limits",
    parse_function=parse_aws_limits_generic,
)


def discover(section: AWSLimitsByRegion) -> DiscoveryResult:
    for region_name in section:
        yield Service(item=region_name)


def check(item: str, params: Mapping[str, Any], section: AWSLimitsByRegion) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    yield from check_aws_limits(
        "sns",
        params,
        data,
    )


_DEFAULT_PARAMETERS_SNS = {
    "topics_standard": (None, 80.0, 90.0),
    "topics_fifo": (None, 80.0, 90.0),
}

register.check_plugin(
    name="aws_sns_limits",
    service_name="AWS/SNS Limits %s",
    discovery_function=discover,
    check_default_parameters=_DEFAULT_PARAMETERS_SNS,
    check_function=check,
    check_ruleset_name="aws_sns_limits",
)
