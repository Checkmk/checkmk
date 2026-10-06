#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)

Section = Mapping[str, set[str]]

AWSNoExceptionsText = "No exceptions"


def parse_aws_exceptions(string_table: list[list[str]]) -> Section:
    parsed: dict[str, set[str]] = {}
    for line in string_table:
        parsed.setdefault(line[0], set()).add(" ".join(line[1:]))
    return parsed


def discover_aws_exceptions(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_aws_exceptions(section: Section) -> CheckResult:
    for title, messages in section.items():
        errors = [message for message in messages if message != AWSNoExceptionsText]
        if errors:
            yield Result(state=State.CRIT, summary="{} {}".format(title, ", ".join(errors)))
        else:
            yield Result(state=State.OK, summary=f"{title} {AWSNoExceptionsText}")


agent_section_aws_exceptions = AgentSection(
    name="aws_exceptions", parse_function=parse_aws_exceptions
)
check_plugin_aws_exceptions = CheckPlugin(
    name="aws_exceptions",
    service_name="AWS Exceptions",
    discovery_function=discover_aws_exceptions,
    check_function=check_aws_exceptions,
)
