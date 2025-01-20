#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated,arg-type"

import ast
import re

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition, STATE_MARKERS
from cmk.agent_based.v2 import render

check_info = {}

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


def parse_filestats(string_table):
    sections_info = {}
    current = []  # should never be used, but better safe than sorry
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


def _parse_filestats_load_lines(info):
    list_of_dicts = []
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


def check_filestats_count(count, params, show_files, reported_lines):
    """common check result - used by main and count_only check"""
    levels = params.get("maxcount", (None, None)) + params.get("mincount", (None, None))
    result = check_levels(
        count,
        "file_count",
        levels,
        infoname="Files in total",
        human_readable_func=lambda i: "%d" % i,
    )
    state, info, perf = result
    if not show_files or state == 0:
        return result

    details = f"{info}\n" + "\n".join([f"[{l['path']}]" for l in reported_lines if l.get("path")])
    return (state, details, perf)


def check_filestats_extremes(files, params, show_files=False):
    """common check result - used by main and extremes_only check"""
    if not files:
        return []
    long_output = {}
    for key, hr_function, minlabel, maxlabel in (
        ("size", render.disksize, "smallest", "largest"),
        ("age", render.timespan, "newest", "oldest"),
    ):
        files_with_metric = [f for f in files if f.get(key) is not None]
        if not files_with_metric:
            continue

        files_with_metric.sort(key=lambda f: f.get(key))  # pylint: disable=cell-var-from-loop
        for efile, label in ((files_with_metric[0], minlabel), (files_with_metric[-1], maxlabel)):
            levels = params.get(f"max{key}_{label}", (None, None)) + params.get(
                f"min{key}_{label}", (None, None)
            )
            yield check_levels(
                efile[key],
                None,
                levels,
                infoname=label.title(),
                human_readable_func=hr_function,
            )

        if not show_files:
            continue

        min_label_levels = params.get(f"max{key}_{minlabel}", (None, None)) + params.get(
            f"min{key}_{minlabel}", (None, None)
        )
        for efile in files_with_metric:
            state, _text, _no_perf = check_levels(
                efile[key],
                None,
                min_label_levels,
            )
            if state == 0:
                break
            if efile["path"] not in long_output:
                text = "Age: {}, Size: {}{}".format(
                    render.timespan(efile["age"]),
                    render.disksize(efile["size"]),
                    STATE_MARKERS[state],
                )
                long_output[efile["path"]] = text

        max_label_levels = params.get(f"max{key}_{maxlabel}", (None, None)) + params.get(
            f"min{key}_{maxlabel}", (None, None)
        )
        for efile in reversed(files_with_metric):
            state, _text, _no_perf = check_levels(
                efile[key],
                None,
                max_label_levels,
            )
            if state == 0:
                break
            if efile["path"] not in long_output:
                text = "Age: {}, Size: {}{}".format(
                    render.timespan(efile["age"]),
                    render.disksize(efile["size"]),
                    STATE_MARKERS[state],
                )
                long_output[efile["path"]] = text

    return ["[%s] %s" % key_text for key_text in sorted(long_output.items())]


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


def check_filestats(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    _output_variety, reported_lines = data
    sumry = [s for s in reported_lines if s.get("type") == "summary"]
    count = sumry[0].get("count", None) if sumry else None

    # only WARN/CRIT files are shown
    show_files = bool(params.get("show_all_files", False))

    if count is not None:
        yield check_filestats_count(count, params, show_files, reported_lines)

    files = [i for i in reported_lines if i.get("type") == "file"]

    if not files:
        return

    # only WARN/CRIT files are shown
    show_files = bool(params.get("show_all_files", False))

    additional_rules = params.get("additional_rules", {})

    matching_files = {}
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
        yield 0, "Additional rules enabled"

        remaining_files_count = count  # for display in service details

        for file_expression, file_details in matching_files.items():
            file_list = file_details["file_list"]
            file_count = len(file_list)
            remaining_files_count -= file_count
            yield 0, "\n%s" % file_details["display_name"]
            yield 0, "Pattern: %r" % file_expression
            yield 0, "Files in total: %d" % file_count
            output = yield from check_filestats_extremes(
                file_list,
                file_details["rules"],
                show_files,
            )
            yield 0, "\n".join(output)

        yield 0, "\nRemaining files: %d" % remaining_files_count

    yield 0, "\n" + "\n".join(remaining_files_output)


def check_filestats_single(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    _output_variety, reported_lines = data
    if len(reported_lines) != 1:
        yield (
            1,
            "Received multiple filestats per single file service. Please check agent plug-in configuration (mk_filestats). For example, if there are multiple non-utf-8 filenames, then they may be mapped to the same file service.",
        )

    single_stat = [i for i in reported_lines if i.get("type") == "file"][0]
    if single_stat.get("size") is None and single_stat.get("age") is None:
        yield 0, f'Status: {single_stat.get("stat_status")}'
        return

    for key, hr_function in (("size", render.disksize), ("age", render.timespan)):
        if (value := single_stat.get(key)) is None:
            continue

        yield check_levels(
            value,
            key if key == "size" else None,
            (
                params.get("max_%s" % key, (None, None))[0],
                params.get("max_%s" % key, (None, None))[1],
                params.get("min_%s" % key, (None, None))[0],
                params.get("min_%s" % key, (None, None))[1],
            ),
            human_readable_func=hr_function,
            infoname=key.title(),
        )


def discover_filestats(section):
    yield from ((item, {}) for item, data in section.items() if data[0] != "single_file")


def discover_filestats_single(section):
    yield from ((item, {}) for item, data in section.items() if data[0] == "single_file")


check_info["filestats.single"] = LegacyCheckDefinition(
    name="filestats_single",
    service_name="File %s",
    sections=["filestats"],
    discovery_function=discover_filestats_single,
    check_function=check_filestats_single,
    check_ruleset_name="filestats_single",
)

check_info["filestats"] = LegacyCheckDefinition(
    name="filestats",
    parse_function=parse_filestats,
    service_name="File group %s",
    discovery_function=discover_filestats,
    check_function=check_filestats,
    check_ruleset_name="filestats",
)
