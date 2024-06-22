#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import urllib.parse
from collections.abc import Mapping, Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib import cache_helper


class PluginData(NamedTuple):
    name: str | None
    state: State
    info: Sequence[str]
    cache_info: cache_helper.CacheInfo | None


MRPESection = Mapping[str, PluginData]


def parse_mrpe(string_table: StringTable) -> MRPESection:
    parsed = {}
    for line in string_table:
        cache_info = cache_helper.CacheInfo.from_raw(line[0], time.time())
        if cache_info:
            line = line[1:]

        # New Linux agent sends (check_name) in first column. Stay
        # compatible with MRPE versions not providing this info
        if line[0].startswith("("):
            name: str | None = line[0].strip("()")
            line = line[1:]
        else:
            name = None

        if len(line) < 2:
            continue

        item, raw_state, line = urllib.parse.unquote(line[0]), line[1], line[2:]

        try:
            state = State(int(raw_state))
        except ValueError:
            line.insert(0, "Invalid plug-in status '%s'. Output is:" % raw_state)
            state = State.UNKNOWN

        # convert to original format by joining and splitting at \1 (which replaced \n)
        text = " ".join(line).split("\1")

        parsed[item] = PluginData(name, state, text, cache_info)

    return parsed


agent_section_mrpe = AgentSection(
    name="mrpe",
    parse_function=parse_mrpe,
)


def discover_mrpe(section: MRPESection) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


class LegacyMetricTuple(NamedTuple):
    name: str
    value: float
    warn: float | None
    crit: float | None
    minn: float | None
    maxx: float | None


def _opt_float(string: str) -> float | None:
    try:
        return float(string)
    except ValueError:
        return None


def _strip_unit_float(string: str) -> float:
    """
    >>> _strip_unit_float("12.3 MB")
    12.3
    """
    for i in range(len(string), 0, -1):
        try:
            return float(string[:i])
        except ValueError:
            pass

    raise ValueError(f"invalid metric value {string!r}")


def _output_metrics(perfdata: Sequence[str]) -> CheckResult:
    for raw_metric in perfdata:
        try:
            yield _parse_nagios_perfstring(raw_metric)
        except ValueError as exc:
            yield Result(
                state=State.UNKNOWN,
                summary=f"Undefined metric: {exc}",
            )


def _parse_nagios_perfstring(perfinfo: str) -> Metric:
    try:
        name, valuetxt = perfinfo.split("=", 1)
    except ValueError:
        raise ValueError(f"{perfinfo!r}")

    if valuetxt.startswith("U"):
        # Nagios perfstrings can start with a value 'U' to indicate an undefined value
        # see https://nagios-plugins.org/doc/guidelines.html#AEN200
        raise ValueError("Nagios style undefined value")

    values = valuetxt.split(";")

    # Levels in perfdata must not contain values with colons.
    # So we split these values and use the upper levels only.
    values = [v.split(":")[-1] for v in values][:5]
    value, warn, crit, min_, max_ = values + [""] * (5 - len(values))

    return Metric(
        name,
        _strip_unit_float(value),
        levels=(_opt_float(warn), _opt_float(crit)),
        boundaries=(_opt_float(min_), _opt_float(max_)),
    )


def check_mrpe(item: str, section: MRPESection) -> CheckResult:
    dataset = section.get(item)
    if dataset is None:
        return

    # First line:  OUTPUT|PERFDATA
    parts = dataset.info[0].split("|", 1)
    output = [parts[0].strip()]
    perfdata = parts[1].strip().split() if len(parts) > 1 else []

    # Further lines
    now_comes_perfdata = False
    for line in dataset.info[1:]:
        if now_comes_perfdata:
            perfdata += line.split()
        else:
            parts = line.split("|", 1)
            output.append(parts[0].strip())
            if len(parts) > 1:
                perfdata += parts[1].strip().split()
                now_comes_perfdata = True

    yield Result(
        state=dataset.state,
        summary=output[0] if output[0] else "No further information available",
        details="\n".join(output) if output[0] else None,
    )
    yield from _output_metrics(perfdata)

    # This is at the end of the summary, to be consistent with local checks.
    if dataset.cache_info is not None:
        yield Result(state=State.OK, summary=cache_helper.render_cache_info(dataset.cache_info))

    # name of check command needed for PNP to choose the correct template
    if dataset.name:
        yield Result(state=State.OK, notice=f"Check command used in metric system: {dataset.name}")


check_plugin_mrpe = CheckPlugin(
    name="mrpe",
    discovery_function=discover_mrpe,
    check_function=check_mrpe,
    service_name="%s",
)
