#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
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


agent_section_gcp_exceptions = AgentSection(name="gcp_exceptions", parse_function=parse)


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


def _parse_error_message(exc_type: str, exc_message: str) -> str:
    match exc_type:
        case "PermissionDenied" if exc_message.startswith("403 Cloud Asset API"):
            return exc_message.split(" [links {")[0]
        case "PermissionDenied" if exc_message.startswith("403 Request denied by Cloud IAM"):
            main_message = exc_message.split(" [links {")[0]
            link_infos = _parse_gcp_links(exc_message.removeprefix(main_message))
            return f"{main_message} {'. '.join(link_infos)}"
        case "PermissionDenied" if exc_message.startswith("403 Permission monitoring"):
            return exc_message
        case "Unauthenticated":
            return exc_message.split(" [reason:")[0]
        case "HttpError":
            return exc_message.split('returned "')[1].split('". Details')[0]
    return exc_message


def check(section: _ExceptionSection) -> CheckResult:
    if section.type is None or section.message is None:
        yield Result(state=State.OK, notice="No exceptions")
    else:
        general_msg = "The Google Cloud API reported an error. Please read the error message on how to fix it:"
        error_msg = _parse_error_message(section.type, section.message)

        if section.gcp_source is not None:
            details = f"{section.type} when trying to access {section.gcp_source}: {error_msg}"
        else:
            details = f"{section.type}: {error_msg}"

        yield Result(state=State.CRIT, summary=f"{general_msg}", details=details)


check_plugin_gcp_exceptions = CheckPlugin(
    name="gcp_exceptions",
    service_name="Exceptions",
    discovery_function=discover,
    check_function=check,
)
