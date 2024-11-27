#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<appdynamics_web_container:sep(124)>>>
# Hans|http-8180|Error Count:0|Busy Threads:0|Current Threads In Pool:0|Request Count:0|Maximum Threads:200
# Hans|jk-8109|Error Count:0|Request Count:2


# mypy: disable-error-code="list-item"

import time
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, render, StringTable

check_info = {}

Section = Mapping[str, Mapping[str, int]]

DiscoveryResult = Iterable[tuple[str, Mapping]]

CheckResult = Iterable[tuple[int, str, list]]


def _parse_metrics(raw_metrics: Sequence[str]) -> Iterable[tuple[str, int]]:
    for metric in raw_metrics:
        name, value = metric.split(":")
        yield name, int(value)


def parse_appdynamics_web_container(string_table: StringTable) -> Section:
    """
    >>> parse_appdynamics_web_container([
    ...    ['line', '1', 'foo:23', 'bar:42'],
    ...    ['line', '2', 'gee:21', 'boo:40'],
    ... ])
    {'line 1': {'foo': 23, 'bar': 42}, 'line 2': {'gee': 21, 'boo': 40}}

    """
    return {" ".join(line[0:2]): dict(_parse_metrics(line[2:])) for line in string_table}


def discover_appdynamics_web_container(section: Section) -> DiscoveryResult:
    yield from ((name, {}) for name in section)


def check_appdynamics_web_container(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (values := section.get(item)) is None:
        return

    error_count = values.get("Error Count", None)
    request_count = values.get("Request Count", None)

    current_threads = values.get("Current Threads In Pool", None)
    busy_threads = values.get("Busy Threads", None)
    max_threads = values.get("Maximum Threads", None)

    if current_threads is not None:
        yield check_levels(
            current_threads,
            "current_threads",
            params["levels"],
            human_readable_func=str,
            infoname="Current threads",
        )

        if max_threads:
            threads_percent = 100.0 * current_threads / max(1, max_threads)
            yield 0, f"{render.percent(threads_percent)} of {max_threads}", []

        if busy_threads is not None:
            yield check_levels(
                busy_threads,
                "busy_threads",
                None,
                human_readable_func=str,
                infoname="Busy threads",
            )

    now = time.time()
    store = get_value_store()
    if error_count is not None:
        yield check_levels(
            get_rate(store, "error", now, error_count, raise_overflow=True),
            "error_rate",
            None,
            human_readable_func=lambda x: f"{x:.2f}/sec",
            infoname="Errors",
        )

    if request_count is not None:
        yield check_levels(
            get_rate(store, "request", now, request_count, raise_overflow=True),
            "request_rate",
            None,
            human_readable_func=lambda x: f"{x:.2f}/sec",
            infoname="Requests",
        )


check_info["appdynamics_web_container"] = LegacyCheckDefinition(
    name="appdynamics_web_container",
    service_name="AppDynamics Web Container %s",
    parse_function=parse_appdynamics_web_container,
    discovery_function=discover_appdynamics_web_container,
    check_function=check_appdynamics_web_container,
    check_ruleset_name="jvm_threads",
    check_default_parameters={"levels": None},
)
