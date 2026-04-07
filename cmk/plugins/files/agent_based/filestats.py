#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import re
from collections.abc import Generator, Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

# params = {
#     "mincount": (tuple, integer),
#     "maxcount": -"-,
#     "minage_oldest": (tuple, seconds),
#     "maxage_oldest":  -"-,
#     "minage_newest": -"-,
#     "maxage_newest": -"-,
#     "minsize_smallest": (tuple, bytes),
#     "maxsize_...
#     "minsize_largest": -"-,
#     "maxsize_...
# }

# 'additional_rules': [('/var/log/sys*', {'maxsize_largest': (1, 2)})]


def _fixed_levels(levels: tuple[float | None, float | None]) -> FixedLevelsT[float] | None:
    warn, crit = levels
    if warn is not None and crit is not None:
        return ("fixed", (warn, crit))
    return None


# .
#   .--Parsing-------------------------------------------------------------.
#   |                  ____                _                               |
#   |                 |  _ \ __ _ _ __ ___(_)_ __   __ _                   |
#   |                 | |_) / _` | '__/ __| | '_ \ / _` |                  |
#   |                 |  __/ (_| | |  \__ \ | | | | (_| |                  |
#   |                 |_|   \__,_|_|  |___/_|_| |_|\__, |                  |
#   |                                              |___/                   |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def parse_filestats(string_table: StringTable) -> dict[str, tuple[str, list[dict[str, Any]]]]:
    sections_info: dict[tuple[str, str], list[str]] = {}
    current: list[str] = []  # should never be used, but better safe than sorry
    for line in string_table:
        if not line:
            continue
        if line[0].startswith("[[["):
            output_variety, subsection_name = line[0][3:-3].split(None, 1)
            current = sections_info.setdefault((output_variety, subsection_name), [])
        else:
            current.append(line[0])

    return {
        name: (variety, _parse_filestats_load_lines(v))
        for (variety, name), v in sections_info.items()
        if v
    }


def _parse_filestats_load_lines(info: list[str]) -> list[dict[str, Any]]:
    list_of_dicts: list[dict[str, Any]] = []
    for line in info:
        try:
            list_of_dicts.append(ast.literal_eval(line))
        except SyntaxError:
            pass
    return list_of_dicts


# .
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_filestats_count(
    count: int, params: Mapping[str, Any], show_files: bool, reported_lines: list[dict[str, Any]]
) -> CheckResult:
    """common check result - used by main and count_only check"""
    results = list(
        check_levels(
            count,
            levels_upper=_fixed_levels(params.get("maxcount", (None, None))),
            levels_lower=_fixed_levels(params.get("mincount", (None, None))),
            metric_name="file_count",
            label="Files in total",
            render_func=lambda i: "%d" % i,
        )
    )
    result = results[0]
    assert isinstance(result, Result)

    if show_files and result.state != State.OK:
        file_details = "\n".join(f"[{l['path']}]" for l in reported_lines if l.get("path"))
        yield Result(
            state=result.state,
            summary=result.summary,
            details=f"{result.summary}\n{file_details}",
        )
    else:
        yield result
    yield from results[1:]


_STATE_MARKERS = {State.OK: "", State.WARN: "(!)", State.CRIT: "(!!)", State.UNKNOWN: "(?)"}


def _get_levels(
    params: Mapping[str, Any], key: str, label: str
) -> tuple[FixedLevelsT[float] | None, FixedLevelsT[float] | None]:
    return (
        _fixed_levels(params.get(f"max{key}_{label}", (None, None))),
        _fixed_levels(params.get(f"min{key}_{label}", (None, None))),
    )


def _check_state(
    value: float,
    levels_upper: FixedLevelsT[float] | None,
    levels_lower: FixedLevelsT[float] | None,
) -> State:
    """Compute the state for a value against levels without yielding results."""
    for r in check_levels(value, levels_upper=levels_upper, levels_lower=levels_lower):
        if isinstance(r, Result):
            return r.state
    return State.OK


def check_filestats_extremes(
    files: list[dict[str, Any]], params: Mapping[str, Any], show_files: bool = False
) -> Generator[Result | Metric, None, list[str]]:
    """common check result - used by main and extremes_only check"""
    if not files:
        return []
    long_output: dict[str, str] = {}
    for key, hr_function, minlabel, maxlabel in (
        ("size", render.disksize, "smallest", "largest"),
        ("age", render.timespan, "newest", "oldest"),
    ):
        files_with_metric = [f for f in files if f.get(key) is not None]
        if not files_with_metric:
            continue

        files_with_metric.sort(key=lambda f: f.get(key, 0))
        for efile, label in ((files_with_metric[0], minlabel), (files_with_metric[-1], maxlabel)):
            levels_upper, levels_lower = _get_levels(params, key, label)
            yield from check_levels(
                efile[key],
                levels_upper=levels_upper,
                levels_lower=levels_lower,
                render_func=hr_function,
                label=label.title(),
            )

        if not show_files:
            continue

        min_levels_upper, min_levels_lower = _get_levels(params, key, minlabel)
        for efile in files_with_metric:
            state = _check_state(efile[key], min_levels_upper, min_levels_lower)
            if state == State.OK:
                break
            if efile["path"] not in long_output:
                long_output[efile["path"]] = "Age: {}, Size: {}{}".format(
                    render.timespan(efile["age"]),
                    render.disksize(efile["size"]),
                    _STATE_MARKERS[state],
                )

        max_levels_upper, max_levels_lower = _get_levels(params, key, maxlabel)
        for efile in reversed(files_with_metric):
            state = _check_state(efile[key], max_levels_upper, max_levels_lower)
            if state == State.OK:
                break
            if efile["path"] not in long_output:
                long_output[efile["path"]] = "Age: {}, Size: {}{}".format(
                    render.timespan(efile["age"]),
                    render.disksize(efile["size"]),
                    _STATE_MARKERS[state],
                )

    return [f"[{key}] {text}" for key, text in sorted(long_output.items())]


# .
#   .--Checks--------------------------------------------------------------.
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_filestats(
    item: str, params: Mapping[str, Any], section: dict[str, tuple[str, list[dict[str, Any]]]]
) -> CheckResult:
    if not (data := section.get(item)):
        return
    _output_variety, reported_lines = data
    sumry = [s for s in reported_lines if s.get("type") == "summary"]
    count = sumry[0].get("count", None) if sumry else None

    # only WARN/CRIT files are shown
    show_files = bool(params.get("show_all_files", False))

    if count is not None:
        yield from check_filestats_count(count, params, show_files, reported_lines)

    files = [i for i in reported_lines if i.get("type") == "file"]

    if not files:
        return

    # only WARN/CRIT files are shown
    show_files = bool(params.get("show_all_files", False))

    additional_rules = params.get("additional_rules", {})

    matching_files: dict[str, dict[str, Any]] = {}
    remaining_files = []
    for efile in files:
        for display_name, file_expression, rules in additional_rules:
            if re.match(file_expression, efile["path"]):
                matching_files.setdefault(
                    file_expression,
                    {
                        "display_name": display_name,
                        "rules": rules,
                        "file_list": [],
                    },
                )["file_list"].append(efile)
                break
        else:
            remaining_files.append(efile)

    remaining_files_output = yield from check_filestats_extremes(
        remaining_files,
        params,
        show_files,
    )

    if count is not None and additional_rules:
        yield Result(state=State.OK, summary="Additional rules enabled")

        remaining_files_count = count  # for display in service details

        for file_expression, file_details in matching_files.items():
            file_list = file_details["file_list"]
            file_count = len(file_list)
            remaining_files_count -= file_count
            if file_details["display_name"]:
                yield Result(state=State.OK, notice=file_details["display_name"])
            yield Result(state=State.OK, summary=f"Pattern: {file_expression!r}")
            yield Result(state=State.OK, summary=f"Files in total: {file_count}")
            output = yield from check_filestats_extremes(
                file_list,
                file_details["rules"],
                show_files,
            )
            if output:
                yield Result(state=State.OK, notice="\n".join(output))

        yield Result(state=State.OK, summary=f"Remaining files: {remaining_files_count}")

    if remaining_files_output:
        yield Result(state=State.OK, notice="\n".join(remaining_files_output))


def check_filestats_single(
    item: str, params: Mapping[str, Any], section: dict[str, tuple[str, list[dict[str, Any]]]]
) -> CheckResult:
    if not (data := section.get(item)):
        return
    _output_variety, reported_lines = data
    if len(reported_lines) != 1:
        yield Result(
            state=State.WARN,
            summary="Received multiple filestats per single file service. Please check agent plug-in configuration (mk_filestats). For example, if there are multiple non-utf-8 filenames, then they may be mapped to the same file service.",
        )

    single_stat = [i for i in reported_lines if i.get("type") == "file"][0]
    if single_stat.get("size") is None and single_stat.get("age") is None:
        yield Result(state=State.OK, summary=f"Status: {single_stat.get('stat_status')}")
        return

    for key, hr_function in (("size", render.disksize), ("age", render.timespan)):
        if (value := single_stat.get(key)) is None:
            continue

        yield from check_levels(
            value,
            levels_upper=_fixed_levels(params.get(f"max_{key}", (None, None))),
            levels_lower=_fixed_levels(params.get(f"min_{key}", (None, None))),
            metric_name=key if key == "size" else None,
            render_func=hr_function,
            label=key.title(),
        )


def discover_filestats(
    section: dict[str, tuple[str, list[dict[str, Any]]]],
) -> DiscoveryResult:
    yield from (Service(item=item) for item, data in section.items() if data[0] != "single_file")


def discover_filestats_single(
    section: dict[str, tuple[str, list[dict[str, Any]]]],
) -> DiscoveryResult:
    yield from (Service(item=item) for item, data in section.items() if data[0] == "single_file")


agent_section_filestats = AgentSection(
    name="filestats",
    parse_function=parse_filestats,
)


check_plugin_filestats_single = CheckPlugin(
    name="filestats_single",
    service_name="File %s",
    sections=["filestats"],
    discovery_function=discover_filestats_single,
    check_function=check_filestats_single,
    check_ruleset_name="filestats_single",
    check_default_parameters={},
)


check_plugin_filestats = CheckPlugin(
    name="filestats",
    service_name="File group %s",
    discovery_function=discover_filestats,
    check_function=check_filestats,
    check_ruleset_name="filestats",
    check_default_parameters={},
)
