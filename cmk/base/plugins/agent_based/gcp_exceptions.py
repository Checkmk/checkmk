#  #!/usr/bin/env python3
#  Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
#  This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
#  conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)


@dataclass(frozen=True)
class _ExceptionSection:
    type: str | None
    message: str | None


def parse(string_table: StringTable) -> _ExceptionSection:
    if len(string_table) == 0:
        return _ExceptionSection(type=None, message=None)
    raw_exception = string_table[0][0]
    exc_type = raw_exception[: raw_exception.find(": ")]
    exc_msg = raw_exception.removeprefix(f"{exc_type}: ")
    return _ExceptionSection(type=exc_type, message=exc_msg)


register.agent_section(name="gcp_exceptions", parse_function=parse)


def discover(section: _ExceptionSection) -> DiscoveryResult:
    yield Service()


def check(section: _ExceptionSection) -> CheckResult:
    if section.type is None or section.message is None:
        yield Result(state=State.OK, notice="No exceptions")
    else:
        general_msg = "The Google Cloud API reported an error. Please read the error message on how to fix it:"
        error_msg = section.message
        if section.type == "PermissionDenied":
            error_msg = section.message.split(" [links {")[0]

        yield Result(
            state=State.CRIT,
            notice=f"{general_msg}\n{section.type}: {error_msg}",
        )


register.check_plugin(
    name="gcp_exceptions",
    service_name="Exceptions",
    discovery_function=discover,
    check_function=check,
)
