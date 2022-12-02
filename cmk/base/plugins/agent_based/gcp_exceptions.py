#  #!/usr/bin/env python3
#  Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
#  This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
#  conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Sequence
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
    gcp_source: str | None


def parse(string_table: StringTable) -> _ExceptionSection:
    if len(string_table) == 0:
        return _ExceptionSection(type=None, message=None, gcp_source=None)
    raw_exception = string_table[0][0]
    exc_type, exc_source, exc_msg = raw_exception.split(":", maxsplit=2)
    return _ExceptionSection(
        type=exc_type, message=exc_msg, gcp_source=exc_source if exc_source != "" else None
    )


register.agent_section(name="gcp_exceptions", parse_function=parse)


def discover(section: _ExceptionSection) -> DiscoveryResult:
    yield Service()


def _parse_gcp_links(links_message: str) -> Sequence[str]:
    """
    >>> _parse_gcp_links(" [links {  description: \\"test_description1:\\"  url: \\"test_url1\\"}links {  description: \\"test_description2:\\"  url: \\"test_url2\\"}]")
    ['test_description1: test_url1', 'test_description2: test_url2']
    """

    def parse_link(link_string: str) -> str:
        link_string = link_string.replace('"', "")
        link_url = link_string.split("url:")[1].strip()
        link_description = (
            link_string.removesuffix(f"url: {link_url}").split("description:")[1].strip()
        )
        return f"{link_description} {link_url}"

    return [
        parse_link(link_string.group(1)) for link_string in re.finditer(r"\{(.*?)\}", links_message)
    ]


def check(section: _ExceptionSection) -> CheckResult:
    if section.type is None or section.message is None:
        yield Result(state=State.OK, notice="No exceptions")
    else:
        general_msg = "The Google Cloud API reported an error. Please read the error message on how to fix it:"
        error_msg = section.message
        if section.type == "PermissionDenied":
            if section.message.startswith("403 Cloud Asset API"):
                error_msg = section.message.split(" [links {")[0]
            elif section.message.startswith("403 Request denied by Cloud IAM"):
                main_message = section.message.split(" [links {")[0]
                link_infos = _parse_gcp_links(section.message.removeprefix(main_message))
                error_msg = f"{main_message} {'. '.join(link_infos)}"
        elif section.type == "HttpError":
            error_msg = section.message.split('returned "')[1].split('". Details')[0]

        if section.gcp_source is not None:
            details = f"{section.type} when trying to access {section.gcp_source}: {error_msg}"
        else:
            details = f"{section.type}: {error_msg}"

        yield Result(state=State.CRIT, summary=f"{general_msg}", details=details)


register.check_plugin(
    name="gcp_exceptions",
    service_name="Exceptions",
    discovery_function=discover,
    check_function=check,
)
