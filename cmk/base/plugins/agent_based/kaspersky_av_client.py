#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Literal, Mapping, TypedDict

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class Section(TypedDict, total=False):
    signature_age: float
    fullscan_age: float
    fullscan_failed: bool


def parse_kaspersky_av_client(string_table: StringTable) -> Section:
    return _parse_kaspersky_av_client(string_table, now=time.time())


def _parse_kaspersky_av_client(string_table: StringTable, now: float) -> Section:
    """
    # Set up timezone to make doctests reproducable.
    >>> import os
    >>> os.environ["TZ"] = "0"

    >>> _parse_kaspersky_av_client([["Fullscan", "01.01.1970", "00:00:00"]], now=1)
    {'fullscan_age': 1.0}
    """
    parsed: Section = {}

    for line in string_table:
        if line[1] == "Missing":
            continue

        date_text = line[1]
        time_text = line[2] if len(line) > 2 else "00:00:00"
        # We assume that the timestamp is to be interpreted in the timezone of
        # the Checkmk server. This might be a problem, if e.g. the agent is located
        # in China and the Checkmk server in USA.
        age = now - time.mktime(time.strptime(f"{date_text} {time_text}", "%d.%m.%Y %H:%M:%S"))

        if line[0] == "Signatures":
            parsed["signature_age"] = age

        elif line[0] == "Fullscan":
            parsed["fullscan_age"] = age

            # handle state of last fullscan if provided
            if len(line) == 4:
                parsed["fullscan_failed"] = line[3] != "0"

    return parsed


register.agent_section(
    name="kaspersky_av_client",
    parse_function=parse_kaspersky_av_client,
)


def discover_kaspersky_av_client(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_kaspersky_av_client(
    params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    """
    >>> test_params = dict(signature_age=(2, 3), fullscan_age=(2, 3))
    >>> test_section = dict(fullscan_age=1.123, signature_age=1.123)
    >>> for result in check_kaspersky_av_client(test_params, test_section):
    ...     result
    Result(state=<State.OK: 0>, summary='Last update of signatures: 1 second ago')
    Result(state=<State.OK: 0>, summary='Last fullscan: 1 second ago')
    """
    yield from _check_age(section, params, "signature_age")
    yield from _check_age(section, params, "fullscan_age")

    if section.get("fullscan_failed"):
        yield Result(state=State.CRIT, summary="Last fullscan failed")


def _check_age(
    section: Section,
    params: Mapping[str, tuple[float, float]],
    key: Literal["signature_age", "fullscan_age"],
) -> CheckResult:
    label = "Last update of signatures" if key == "signature_age" else "Last fullscan"
    if (age := section.get(key)) is None:
        yield Result(state=State.UNKNOWN, summary=f"{label} unkown")
        return

    yield from check_levels(
        value=age,
        levels_upper=params[key],
        label=label,
        render_func=lambda v: f"{render.timespan(v)} ago",
    )


register.check_plugin(
    name="kaspersky_av_client",
    service_name="Kaspersky AV",
    discovery_function=discover_kaspersky_av_client,
    check_function=check_kaspersky_av_client,
    check_default_parameters={
        "signature_age": (86400, 7 * 86400),
        "fullscan_age": (86400, 7 * 86400),
    },
    check_ruleset_name="kaspersky_av_client",
)
