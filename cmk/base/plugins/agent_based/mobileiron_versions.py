#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import datetime
from typing import TypedDict

from .agent_based_api.v1 import regex, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.mobileiron import Section


class Params(TypedDict):
    patchlevel_unparsable: int
    patchlevel_age: int
    os_build_unparsable: int
    os_age: int
    ios_version_regexp: str
    android_version_regexp: str
    os_version_other: int


def is_too_old(date_string: str, seconds: float) -> tuple[bool, int]:
    """Return True if the date is older than the number of seconds.
    Plus the number of days old.
    """

    threshold = datetime.timedelta(seconds=seconds)
    for fmt, fmt_len in (("%Y-%m-%d", 10), ("%y%m%d", 6)):
        try:
            dt = datetime.datetime.now() - datetime.datetime.strptime(date_string[:fmt_len], fmt)
            return dt > threshold, dt.days
        except ValueError:
            continue

    raise ValueError("Cannot parse the date")


def _check_android_patch_level(params: Params, patch_level: str) -> CheckResult:

    try:
        security_patch_is_too_old, days_old = is_too_old(patch_level, params["patchlevel_age"])
    except ValueError:
        yield Result(
            state=State(params["patchlevel_unparsable"]),
            summary=f"Security patch level has an invalid date format: {patch_level}",
        )
    else:
        if security_patch_is_too_old is True:
            yield Result(
                state=State.CRIT,
                summary=f"Security patch level date is {days_old} days old: {patch_level}",
            )
        else:
            yield Result(
                state=State.OK,
                summary=f"Security patch level: {patch_level}",
            )


def _check_os_build_version(params: Params, section: Section) -> CheckResult:
    try:
        build_version_is_too_old, days_old = is_too_old(
            str(section.osBuildVersion), params["os_age"]
        )
    except ValueError:
        yield Result(
            state=State(params["os_build_unparsable"]),
            summary=f"OS build version has an invalid date format: {section.osBuildVersion}",
        )
    else:
        if build_version_is_too_old is True:
            yield Result(
                state=State.CRIT,
                summary=f"OS build version is {days_old} days old: {section.osBuildVersion}",
            )

        else:
            yield Result(
                state=State.OK,
                summary=f"OS build version: {section.osBuildVersion}",
            )


def _check_os_version(section: Section, user_regex: str) -> Result:
    if not user_regex:
        return Result(
            state=State.OK,
            summary=f"OS version: {section.platformVersion}",
        )
    try:
        match = regex(user_regex).search(str(section.platformVersion))
    except Exception:
        match = None
    if match:
        return Result(
            state=State.OK,
            summary=f"OS version: {section.platformVersion}",
        )
    return Result(
        state=State.CRIT,
        summary=f"OS version mismatch: {section.platformVersion}",
    )


def check_mobileiron_versions(params: Params, section: Section) -> CheckResult:

    yield from _check_os_build_version(params, section)

    if section.androidSecurityPatchLevel:
        yield from _check_android_patch_level(params, section.androidSecurityPatchLevel)

    if section.platformType == "ANDROID":
        yield _check_os_version(section, params["android_version_regexp"])
    elif section.platformType == "IOS":
        yield _check_os_version(section, params["ios_version_regexp"])
    else:
        yield Result(
            state=State(params["os_version_other"]),
            summary=f"OS version: {section.platformVersion}",
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
    check_ruleset_name="mobileiron_versions",
    check_default_parameters={
        "patchlevel_unparsable": 0,
        "patchlevel_age": 7776000,
        "os_build_unparsable": 0,
        "os_age": 7776000,
        "ios_version_regexp": "",
        "android_version_regexp": "",
        "os_version_other": 0,
    },
)
