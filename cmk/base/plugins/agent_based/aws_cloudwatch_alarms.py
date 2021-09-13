#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final, Mapping

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.aws import GenericAWSSection, parse_aws

_AWS_CLOUDWATCH_ALARM_STATES: Final[Mapping[str, State]] = {
    "no_alarms": State.OK,
    "ok": State.OK,
    "alarm": State.CRIT,
    "insufficient_data": State.WARN,
}

_AWS_CLOUDWATCH_ALARM_TEXTS: Final[Mapping[str, str]] = {
    "no_alarms": "no alarms",
    "ok": "OK",
    "alarm": "alarm",
    "insufficient_data": "insufficient data",
}


def discover_aws_cloudwatch_alarms(section: GenericAWSSection) -> DiscoveryResult:
    yield Service()


def _make_result(alarm_state: str, alarm_name: str) -> Result:
    return Result(
        state=_AWS_CLOUDWATCH_ALARM_STATES.get(alarm_state, State.UNKNOWN),
        notice="%s: %s"
        % (
            alarm_name,
            _AWS_CLOUDWATCH_ALARM_TEXTS.get(alarm_state, f"unknown[{alarm_state}]"),
        ),
    )


def check_aws_cloudwatch_alarms(section: GenericAWSSection) -> CheckResult:
    yield from (_make_result(alarm["StateValue"].lower(), alarm["AlarmName"]) for alarm in section)


register.agent_section(
    name="aws_cloudwatch_alarms",
    parse_function=parse_aws,
)

register.check_plugin(
    name="aws_cloudwatch_alarms",
    service_name="AWS/CloudWatch Alarms",
    discovery_function=discover_aws_cloudwatch_alarms,
    check_function=check_aws_cloudwatch_alarms,
)
