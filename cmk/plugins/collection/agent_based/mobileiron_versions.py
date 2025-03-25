#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import contextlib
import datetime
import re
from typing import TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.mobileiron import Section


class Params(TypedDict):
    patchlevel_unparsable: int
    patchlevel_age: int
    os_build_unparsable: int
    os_age: int
    ios_version_regexp: str
    android_version_regexp: str
    os_version_other: int


def _try_calculation_age(date_string: str) -> int:
    """
    Parse a date string. A date string can be in "%Y-%m-%d" or "%y%m%d" format.
    Return a timedelta between now and the parsed string.
    """

    for fmt, fmt_len in (("%Y-%m-%d", 10), ("%y%m%d", 6)):
        with contextlib.suppress(ValueError):
            delta = datetime.datetime.now() - datetime.datetime.strptime(date_string[:fmt_len], fmt)
            return int(delta.total_seconds())

    raise ValueError("Cannot parse the date")


def _check_android_patch_level(params: Params, patch_level: str) -> CheckResult:
    level_days = int(datetime.timedelta(seconds=params["patchlevel_age"]).total_seconds())
    try:
        age = _try_calculation_age(patch_level)
    except ValueError:
        yield Result(
            state=State(params["patchlevel_unparsable"]),
            summary=f"Security patch level has an invalid date format: '{patch_level}'",
        )
    else:
        yield from check_levels_v1(
            label=f"Security patch level is '{patch_level}'",
            metric_name="mobileiron_last_patched",
            value=age,
            levels_upper=(level_days, level_days),
            render_func=render.timespan,
        )


def _check_os_build_version(params: Params, section: Section) -> CheckResult:
    level_days = int(datetime.timedelta(seconds=params["os_age"]).total_seconds())
    try:
        age = _try_calculation_age(str(section.os_build_version))
    except ValueError:
        yield Result(
            state=State(params["os_build_unparsable"]),
            notice=f"OS build version has an invalid date format: '{section.os_build_version}'",
        )
    else:
        yield from check_levels_v1(
            label=f"OS build version is '{section.os_build_version}'",
            metric_name="mobileiron_last_build",
            value=age,
            levels_upper=(level_days, level_days),
            render_func=render.timespan,
            notice_only=True,
        )


def _check_os_version(section: Section, user_regex: str) -> Result:
    if not user_regex:
        return Result(
            state=State.OK,
            notice=f"OS version: {section.platform_version}",
        )
    try:
        match = re.search(user_regex, str(section.platform_version))
    except Exception:
        match = None
    if match:
        return Result(
            state=State.OK,
            notice=f"OS version: {section.platform_version}",
        )
    return Result(
        state=State.CRIT,
        notice=f"OS version mismatch: {section.platform_version}",
    )


def check_mobileiron_versions(params: Params, section: Section) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"Client version: {section.client_version}",
    )

    if section.android_security_patch_level:
        yield from _check_android_patch_level(params, section.android_security_patch_level)

    yield from _check_os_build_version(params, section)

    if section.platform_type == "ANDROID":
        yield _check_os_version(section, params["android_version_regexp"])
    elif section.platform_type == "IOS":
        yield _check_os_version(section, params["ios_version_regexp"])
    else:
        yield Result(
            state=State(params["os_version_other"]),
            summary=f"OS version: {section.platform_version}",
        )


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


check_plugin_mobileiron_versions = CheckPlugin(
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
