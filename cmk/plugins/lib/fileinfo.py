#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fnmatch
import re
import time
from collections.abc import Callable, Iterable, Mapping
from enum import Enum
from re import Match
from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, render, Result, Service, State

from . import eval_regex
from .interfaces import saveint

DiscoveryParams = Iterable[Mapping[str, list[tuple[str, str | tuple[str, str]]]]]


class FileinfoItem(NamedTuple):
    name: str
    missing: bool
    failed: bool
    size: int | None
    time: int | None


class Fileinfo(NamedTuple):
    reftime: int | None = None
    files: dict[str, FileinfoItem] = {}


class FileStats(NamedTuple):
    name: str
    status: str
    size: int | None = None
    time: int | None = None


class CheckType(Enum):
    SINGLE = "single"
    GROUP = "group"


class MetricInfo(NamedTuple):
    title: str
    key: str
    value: int | None
    verbose_func: Callable


_DATE_MACRO_PATTERN = re.compile(r"\$(DATE|YESTERDAY):((?:%\w.?){1,})\$")


def _cast_value(value: Any, data_type: type) -> Any:
    try:
        return data_type(value)
    except (ValueError, TypeError):
        return None


def _get_field(row: list[Any], index: int) -> Any:
    try:
        return row[index]
    except IndexError:
        return None


def _parse_single_legacy_row(row: list[str]) -> FileStats | None:
    name = _cast_value(row[0], str)
    if not name or name.endswith("No such file or directory"):
        # endswith("No such file...") is needed to
        # support the very old solaris perl based version of fileinfo
        return None

    size = _get_field(row, 1)
    if size == "missing":
        return FileStats(name=name, status="missing")

    if size in ("not readable", ""):
        return FileStats(name=name, status="stat failed")

    return FileStats(
        name=name,
        size=_cast_value(size, int),
        time=_cast_value(_get_field(row, 2), int),
        status="ok",
    )


def _parse_single_row(row: list[str], header: Iterable[str]) -> FileStats | None:
    file_data = dict(zip(header, row))

    name = _cast_value(file_data.get("name"), str)
    status = _cast_value(file_data.get("status"), str)

    if not name or not status:
        return None

    return FileStats(
        name=name,
        status=status,
        size=_cast_value(file_data.get("size"), int),
        time=_cast_value(file_data.get("time"), int),
    )


def _construct_fileinfo_item(file_stats: FileStats) -> FileinfoItem:
    return FileinfoItem(
        file_stats.name,
        "missing" in file_stats.status,
        "stat failed" in file_stats.status,
        file_stats.size,
        file_stats.time,
    )


def parse_fileinfo(string_table: StringTable) -> Fileinfo:
    if not string_table:
        return Fileinfo()

    reftime = _cast_value(string_table[0][0], int)
    files = {}

    if len(string_table) == 1:
        return Fileinfo(reftime=reftime)

    iter_info = iter(string_table)
    header = None

    for row in iter_info:
        if len(row) == 1:
            # the validation whether a section is legacy has to be done inside
            # the loop, because sections might be consolidated, resulting in a
            # legacy section appended to a current section, or vice versa.
            # we have seen this when users monitor both SAP HANA and "regular"
            # files.
            if row == ["[[[header]]]"]:
                # non-legacy
                header = next(iter_info)
                continue
            if row[0].isdigit():
                # designates a timestamp; if following this there is a header (as above),
                # the section is not legacy
                header = None
                continue
            continue

        if header is not None:
            file_stats = _parse_single_row(row, header)
        else:
            file_stats = _parse_single_legacy_row(row)

        if not file_stats:
            continue
        files[file_stats.name] = _construct_fileinfo_item(file_stats)

    return Fileinfo(reftime=reftime, files=files)


def _match(name: str, pattern: str) -> bool | Match | None:
    return (
        re.match(pattern[1:], name)
        if pattern.startswith("~")
        else fnmatch.fnmatch(name, pattern)  #
    )


def fileinfo_process_date(pattern: str, reftime: int) -> str:
    r"""Replace date macros like "$DATE:%Y%m%d$" in the pattern

    * You can have both macros in the string
    * Multiple occurances are considered
    """

    def fileinfo_date_macro_replacer(m: re.Match) -> str:
        offset = 0 if m.group(1) == "DATE" else 86400
        return time.strftime(m.group(2), time.localtime(reftime - offset))

    return _DATE_MACRO_PATTERN.sub(fileinfo_date_macro_replacer, pattern)


def fileinfo_groups_get_group_name(
    group_patterns: list[tuple[str, str | tuple[str, str]]],
    filename: str,
    reftime: int,
) -> dict[str, list[str | tuple[str, str]]]:
    found_these_groups: dict[str, set] = {}

    for group_name, pattern in group_patterns:
        if isinstance(pattern, str):  # support old format
            inclusion, exclusion = pattern, ""
        else:
            inclusion, exclusion = pattern

        if _match(filename, exclusion):
            continue

        inclusion = (
            ("~" + fileinfo_process_date(inclusion[1:], reftime))
            if inclusion.startswith("~")
            else fileinfo_process_date(inclusion, reftime)
        )

        incl_match = _match(filename, inclusion)
        if not incl_match:
            continue

        matches = []
        num_perc_s = 0
        if isinstance(incl_match, re.Match):  # it's match object then!
            num_perc_s = group_name.count("%s")
            matches = [g and g or "" for g in incl_match.groups()]

            if len(matches) < num_perc_s:
                raise RuntimeError(
                    "Invalid entry in inventory_fileinfo_groups: "
                    "group name '%s' contains %d times '%%s', but regular expression "
                    "'%s' contains only %d subexpression(s)."
                    % (group_name, num_perc_s, inclusion, len(matches))
                )

        this_pattern: str | tuple[str, str] = ""
        if matches:
            for nr, group in enumerate(matches):
                inclusion = eval_regex.instantiate_regex_pattern_once(inclusion, group)
                group_name = group_name.replace("%%%d" % (nr + 1), group)

            this_group_name = group_name % tuple(matches[:num_perc_s])
            this_pattern = ("~%s" % inclusion, exclusion)

        else:
            this_group_name = group_name
            this_pattern = pattern

        found_these_groups.setdefault(this_group_name, set()).add(this_pattern)

    # Convert pattern containers to lists (sets are not possible in autochecks)
    # It is possible now. keep this to not break the "append" in the check function
    return {k: list(v) for k, v in found_these_groups.items()}


def discovery_fileinfo_common(
    params: DiscoveryParams,
    section: Fileinfo,
    check_type: CheckType,
) -> DiscoveryResult:
    reftime = section.reftime
    if reftime is None:
        return

    for item in section.files.values():
        found_groups = {}
        for param in params:
            group_patterns = param.get("group_patterns", [])
            found_groups.update(fileinfo_groups_get_group_name(group_patterns, item.name, reftime))

        if not found_groups and check_type == CheckType.SINGLE and not item.missing:
            yield Service(item=item.name)

        elif found_groups and check_type == CheckType.GROUP:
            for group_name, patterns in found_groups.items():
                yield Service(item=group_name, parameters={"group_patterns": patterns})


def discovery_fileinfo(
    params: DiscoveryParams,
    section: Fileinfo,
) -> DiscoveryResult:
    yield from discovery_fileinfo_common(params, section, CheckType.SINGLE)


def discovery_fileinfo_groups(
    params: DiscoveryParams,
    section: Fileinfo,
) -> DiscoveryResult:
    yield from discovery_fileinfo_common(params, section, CheckType.GROUP)


def _fileinfo_check_function(
    check_definition: list[MetricInfo],
    params: Mapping[str, Any],
) -> CheckResult:
    for metric in check_definition:
        if metric.value is None:
            continue

        # if the age of the file is negative but falls within the negative_age_tolerance
        # period, set the age to 0
        tolerance = params.get("negative_age_tolerance", 0)
        adjusted_metric_value = (
            0
            if "age" in metric.title.lower() and metric.value < 0 and abs(metric.value) <= tolerance
            else metric.value
        )

        if "age" in metric.title.lower() and adjusted_metric_value < 0:
            age = metric.verbose_func(abs(adjusted_metric_value))
            message = (
                "The timestamp of the file is in the future. Please investigate your host times"
            )

            yield Result(state=State.UNKNOWN, summary=f"{metric.title}: -{age}, {message}")
            yield Metric(metric.key, adjusted_metric_value)

            continue

        max_levels = params.get("max" + metric.key, (None, None))
        min_levels = params.get("min" + metric.key, (None, None))

        yield from check_levels_v1(
            adjusted_metric_value,
            levels_upper=max_levels,
            levels_lower=min_levels,
            metric_name=metric.key,
            label=metric.title,
            render_func=metric.verbose_func,
        )


def check_fileinfo_data(
    file_info: FileinfoItem | None,
    reftime: int,
    params: Mapping[str, Any],
) -> CheckResult:
    if file_info is not None and not file_info.missing:
        if file_info.failed:
            yield Result(state=State.WARN, summary="File stat failed")

        elif file_info.time is None:
            yield Result(state=State.WARN, summary="File stat time failed")

        else:
            age = reftime - file_info.time
            check_definition = [
                MetricInfo("Size", "size", file_info.size, render.bytes),
                MetricInfo("Age", "age", age, render.timespan),
            ]
            yield from _fileinfo_check_function(check_definition, params)

    else:
        yield Result(
            state=State(value=params.get("state_missing", State.UNKNOWN)), summary="File not found"
        )


def _filename_matches(
    filename: str,
    reftime: int,
    inclusion: str,
    exclusion: str,
) -> tuple[bool, str]:
    date_inclusion = ""
    inclusion_is_regex = False
    exclusion_is_regex = False

    if inclusion.startswith("~"):
        inclusion_is_regex = True
        inclusion = inclusion[1:]
    if exclusion.startswith("~"):
        exclusion_is_regex = True
        exclusion = exclusion[1:]

    inclusion_tmp = fileinfo_process_date(inclusion, reftime)
    if inclusion != inclusion_tmp:
        inclusion = inclusion_tmp
        date_inclusion = inclusion_tmp

    incl_match: bool | Match | None = None
    if inclusion_is_regex:
        incl_match = re.match(inclusion, filename)
    else:
        incl_match = fnmatch.fnmatch(filename, inclusion)

    excl_match: bool | Match | None = None
    if exclusion_is_regex:
        excl_match = re.match(exclusion, filename)
    else:
        excl_match = fnmatch.fnmatch(filename, exclusion)

    if incl_match and not excl_match:
        return True, date_inclusion
    return False, date_inclusion


def _update_minmax(
    new_value: int,
    current_minmax: tuple[int, int] | None,
) -> tuple[int, int]:
    if not current_minmax:
        return new_value, new_value

    current_min, current_max = current_minmax

    return min(new_value, current_min), max(new_value, current_max)


def _check_individual_files(
    params: Mapping[str, Any],
    file_name: str,
    file_size: int,
    file_age: int,
    skip_ok_files: bool,
) -> CheckResult:
    """
    This function checks individual files against levels defined for the file group.
    This is done to generate information for the long output.
    """

    # if the age of the file is negative but falls within the negative_age_tolerance
    # period, set the age to 0
    tolerance = params.get("negative_age_tolerance", 0)
    adjusted_file_age = 0 if file_age < 0 and abs(file_age) <= tolerance else file_age

    for key, value in [
        ("age_oldest", adjusted_file_age),
        ("age_newest", adjusted_file_age),
        ("size_smallest", file_size),
        ("size_largest", file_size),
    ]:
        levels_upper = params.get("max" + key, (None, None))
        levels_lower = params.get("min" + key, (None, None))
        results = check_levels_v1(
            value,
            metric_name=key,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
        )

    overall_state = max(r.state.value for r in results if isinstance(r, Result))
    if skip_ok_files and State(overall_state) == State.OK:
        return

    size = render.bytes(file_size)
    age = render.timespan(abs(adjusted_file_age))

    if adjusted_file_age < 0:
        message = "The timestamp of the file is in the future. Please investigate your host times"
        yield Result(
            state=State.UNKNOWN, summary=f"[{file_name}] Age: -{age}, Size: {size}, {message}"
        )
        return

    yield Result(
        state=State.OK,
        notice=f"[{file_name}] Age: {age}, Size: {size}",
    )


def _define_fileinfo_group_check(
    files_matching: dict[str, Any],
) -> list[MetricInfo]:
    size_smallest, size_largest = files_matching["size_minmax"] or (None, None)
    age_newest, age_oldest = files_matching["age_minmax"] or (None, None)
    return [
        MetricInfo("Count", "count", files_matching["count_all"], saveint),
        MetricInfo("Size", "size", files_matching["size_all"], render.bytes),
        MetricInfo("Largest size", "size_largest", size_largest, render.bytes),
        MetricInfo("Smallest size", "size_smallest", size_smallest, render.bytes),
        MetricInfo("Oldest age", "age_oldest", age_oldest, render.timespan),
        MetricInfo("Newest age", "age_newest", age_newest, render.timespan),
    ]


def _fileinfo_check_conjunctions(
    check_definition: list[MetricInfo],
    params: Mapping[str, Any],
) -> CheckResult:
    conjunctions = params.get("conjunctions", [])
    for conjunction_state, levels in conjunctions:
        levels = dict(levels)
        match_texts = []
        matches = 0
        for title, key, value, readable_f in check_definition:
            level = levels.get(key)
            if level is not None and value and value is not None and value >= level:
                match_texts.append(f"{title.lower()} at {readable_f(level)}")
                matches += 1

            level_lower = levels.get("%s_lower" % key)
            if level_lower is not None and value is not None and value < level_lower:
                match_texts.append(f"{title.lower()} below {readable_f(level_lower)}")
                matches += 1

        if matches == len(levels):
            yield Result(
                state=State(conjunction_state),
                summary="Conjunction: %s" % " AND ".join(match_texts),
            )


def check_fileinfo_groups_data(
    item: str,
    params: Mapping[str, Any],
    section: Fileinfo,
    reftime: int,
) -> CheckResult:
    date_inclusion = None
    files_stat_failed = set()
    files_matching: dict[str, Any] = {
        "count_all": 0,
        "size_all": 0,
        "size_minmax": None,
        "age_minmax": None,
        "file_text": {},
    }

    raw_group_patterns = params.get("group_patterns")
    skip_ok_files = params.get("shorten_multiline_output", False)

    if not raw_group_patterns:
        yield Result(state=State.UNKNOWN, summary="No group pattern found.")
        return

    group_patterns = {(p, "") if isinstance(p, str) else p for p in raw_group_patterns}

    include_patterns = [i for i, _e in group_patterns]
    exclude_patterns = [e for _i, e in group_patterns if e != ""]

    yield Result(state=State.OK, notice="Include patterns: %s" % ", ".join(include_patterns))

    if exclude_patterns:
        yield Result(state=State.OK, notice="Exclude patterns: %s" % ", ".join(exclude_patterns))

    # Start counting values on all files
    for file_stat in section.files.values():
        if file_stat.missing:
            continue

        for inclusion, exclusion in group_patterns:
            filename_matches, date_inclusion = _filename_matches(
                file_stat.name, reftime, inclusion, exclusion
            )
            if not filename_matches:
                continue
            if file_stat.failed:
                files_stat_failed.add(file_stat.name)
                break

            if file_stat.size is None or file_stat.time is None:
                continue

            files_matching["size_all"] += file_stat.size
            files_matching["count_all"] += 1

            files_matching["size_minmax"] = _update_minmax(
                file_stat.size, files_matching["size_minmax"]
            )

            age = reftime - file_stat.time
            files_matching["age_minmax"] = _update_minmax(age, files_matching["age_minmax"])

            yield from _check_individual_files(
                params, file_stat.name, file_stat.size, age, skip_ok_files
            )

            break

    # Start Checking
    if date_inclusion:
        yield Result(state=State.OK, summary=f"Date pattern: {date_inclusion}")

    check_definition = _define_fileinfo_group_check(files_matching)

    if files_stat_failed:
        yield Result(
            state=State.WARN, summary="Files with unknown stat: %s" % ", ".join(files_stat_failed)
        )

    yield from _fileinfo_check_function(check_definition, params)
    yield from _fileinfo_check_conjunctions(check_definition, params)
