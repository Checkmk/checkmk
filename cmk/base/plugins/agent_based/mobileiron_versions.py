#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
from typing import Any, Mapping, Optional

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.mobileiron import Section


def is_too_old(date_string: Optional[str], months: int = 3) -> bool:
    """Return True if the date is older than the number of months.

    >>> is_too_old("2021-04-23")
    True
    >>> is_too_old("2129-04-23")
    False
    """

    if not date_string:
        raise ValueError("Date_string cannot be empty")

    threshold = datetime.timedelta(days=months * 30)
    for fmt, fmt_len in (("%Y-%m-%d", 10), ("%y%m%d", 6)):
        try:
            dt = datetime.datetime.now() - datetime.datetime.strptime(date_string[:fmt_len], fmt)
            return dt > threshold
        except ValueError:
            continue

    raise ValueError("Cannot parse the date")


def check_mobileiron_versions(params: Mapping[str, Any], section: Section) -> CheckResult:

    try:
        build_version_is_too_old = is_too_old(section.osBuildVersion)
    except ValueError:
        yield Result(
            state=State.UNKNOWN,
            summary=f"OS build version has an invalid date format: {section.osBuildVersion}",
        )
    else:
        if build_version_is_too_old is True:
            yield Result(
                state=State.WARN,
                summary=f"OS build version is more than 3 months old: {section.osBuildVersion}",
            )

        else:
            yield Result(
                state=State.OK,
                summary=f"OS build version: {section.osBuildVersion}",
            )

    try:
        security_patch_is_too_old = is_too_old(section.androidSecurityPatchLevel)
    except ValueError:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Security patch level has an invalid date format: {section.androidSecurityPatchLevel}",
        )
    else:
        if security_patch_is_too_old is True:
            yield Result(
                state=State.WARN,
                summary=f"Security patch level date is more than 3 months old: {section.androidSecurityPatchLevel}",
            )
        else:
            yield Result(
                state=State.OK,
                summary=f"Security patch level: {section.androidSecurityPatchLevel}",
            )

    yield Result(
        state=State.OK,
        summary=f"Platform version: {section.platformVersion}",
    )

    yield Result(
        state=State.OK,
        summary=f"Client version: {section.clientVersion}",
    )


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


register.check_plugin(
    name="mobileiron_versions",
    sections=["mobileiron_section"],
    service_name="Mobileiron versions",
    discovery_function=discover_single,
    check_function=check_mobileiron_versions,
    check_default_parameters={},
)
