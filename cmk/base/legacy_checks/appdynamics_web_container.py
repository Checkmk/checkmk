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

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import get_rate, get_value_store
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

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
    item: str, params: tuple | None, section: Section
) -> CheckResult:
    if (values := section.get(item)) is None:
        return

    error_count = values.get("Error Count", None)
    request_count = values.get("Request Count", None)

    current_threads = values.get("Current Threads In Pool", None)
    busy_threads = values.get("Busy Threads", None)
    max_threads = values.get("Maximum Threads", None)

    if isinstance(params, tuple):
        warn, crit = params
    else:
        warn, crit = (None, None)

    if current_threads is not None:
        state = 0
        if crit and current_threads >= crit:
            state = 2
        elif warn and current_threads >= warn:
            state = 1

        thread_levels_label = ""
        if state > 0:
            thread_levels_label = " (warn/crit at %d/%d)" % (warn, crit)  # type: ignore # it's fine...

        if max_threads is not None:
            perfdata = [("current_threads", current_threads, warn, crit, 0, max_threads)]
            threads_percent = 100.0 * current_threads / max(1, max_threads)
            max_info = " of %d (%.2f%%)" % (max_threads, threads_percent)
        else:
            perfdata = [("current_threads", current_threads, warn, crit)]
            max_info = ""
        yield state, "Current threads: %d%s%s" % (
            current_threads,
            max_info,
            thread_levels_label,
        ), perfdata

        if busy_threads is not None:
            perfdata = [("busy_threads", busy_threads)]
            yield 0, "Busy threads: %d" % busy_threads, perfdata

    now = time.time()

    if error_count is not None:
        rate_id = "appdynamics_web_container.%s.error" % (item.lower().replace(" ", "_"))
        error_rate = get_rate(get_value_store(), rate_id, now, error_count, raise_overflow=True)
        perfdata = [("error_rate", error_rate)]
        yield 0, "Errors: %.2f/sec" % error_rate, perfdata

    if request_count is not None:
        rate_id = "appdynamics_web_container.%s.request" % (item.lower().replace(" ", "_"))
        request_rate = get_rate(get_value_store(), rate_id, now, request_count, raise_overflow=True)
        perfdata = [("request_rate", request_rate)]
        yield 0, "Requests: %.2f/sec" % request_rate, perfdata


check_info["appdynamics_web_container"] = LegacyCheckDefinition(
    service_name="AppDynamics Web Container %s",
    parse_function=parse_appdynamics_web_container,
    discovery_function=discover_appdynamics_web_container,
    check_function=check_appdynamics_web_container,
    check_ruleset_name="jvm_threads",
)
