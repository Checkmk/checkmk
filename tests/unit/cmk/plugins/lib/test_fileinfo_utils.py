#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
import time_machine

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import CheckResult, Metric, render, Result, State
from cmk.plugins.lib.fileinfo import (
    _cast_value,
    _fileinfo_check_conjunctions,
    _fileinfo_check_function,
    _filename_matches,
    _get_field,
    _parse_single_legacy_row,
    check_fileinfo_data,
    check_fileinfo_groups_data,
    Fileinfo,
    fileinfo_groups_get_group_name,
    fileinfo_process_date,
    FileinfoItem,
    MetricInfo,
    parse_fileinfo,
)


@pytest.mark.parametrize(
    "value, cast_type",
    [
        (None, float),
        ("some string", int),
    ],
)
def test__cast_value(value: str | None, cast_type: type[float] | type[int]) -> None:
    cast_value = _cast_value(value, cast_type)
    assert cast_value is None


def test__get_field() -> None:
    my_list = [1, 2, 3]
    field_value = _get_field(my_list, 3)
    assert field_value is None


def test__parse_single_legacy_row() -> None:
    row = ["No such file or directory"]
    parsed_row = _parse_single_legacy_row(row)
    assert not parsed_row


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["1415625919"],
                ["string"],
                ["C:\\Datentransfer\\ORU\\KC\\dummy.txt", "1917", "1189173868"],
                ["C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7", "2414", "1415625918"],
                ["C:\\Datentransfer\\ORU\\KC\\KC_41135.sem", "1", "1415625918"],
            ],
            Fileinfo(
                files={
                    "C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7": FileinfoItem(
                        name="C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7",
                        missing=False,
                        failed=False,
                        size=2414,
                        time=1415625918,
                    ),
                    "C:\\Datentransfer\\ORU\\KC\\KC_41135.sem": FileinfoItem(
                        name="C:\\Datentransfer\\ORU\\KC\\KC_41135.sem",
                        missing=False,
                        failed=False,
                        size=1,
                        time=1415625918,
                    ),
                    "C:\\Datentransfer\\ORU\\KC\\dummy.txt": FileinfoItem(
                        name="C:\\Datentransfer\\ORU\\KC\\dummy.txt",
                        missing=False,
                        failed=False,
                        size=1917,
                        time=1189173868,
                    ),
                },
                reftime=1415625919,
            ),
        ),
        (
            [
                ["1415625919"],
                ["No such file or directory", 4, 5],
                ["C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7", "2414", "1415625918"],
                ["C:\\Datentransfer\\ORU\\KC\\KC_41135.sem", "1", "1415625918"],
            ],
            Fileinfo(
                files={
                    "C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7": FileinfoItem(
                        name="C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7",
                        missing=False,
                        failed=False,
                        size=2414,
                        time=1415625918,
                    ),
                    "C:\\Datentransfer\\ORU\\KC\\KC_41135.sem": FileinfoItem(
                        name="C:\\Datentransfer\\ORU\\KC\\KC_41135.sem",
                        missing=False,
                        failed=False,
                        size=1,
                        time=1415625918,
                    ),
                },
                reftime=1415625919,
            ),
        ),
        (
            [
                ["1415625919"],
                ["[[[header]]]"],
                ["name", "status", "size", "time"],
                ["", "2414", "1415625918"],
            ],
            Fileinfo(reftime=1415625919, files={}),
        ),
    ],
)
def test_parse_fileinfo(info: StringTable, expected_result: Fileinfo) -> None:
    assert parse_fileinfo(info) == expected_result


@pytest.mark.parametrize(
    "group_patterns, filename, reftime, expected_result",
    [
        (
            [("name", "~filename*")],
            "filename_aa",
            123456,
            {"name": ["~filename*"]},
        ),
        (
            [("name", ("", "filename*"))],
            "filename_aa",
            123456,
            {},
        ),
        (
            [("name", ("~(file)", ""))],
            "file1file2file3",
            123456,
            {"name": [("~~file", "")]},
        ),
    ],
)
def test_fileinfo_groups_get_group_name(
    group_patterns: list[tuple[str, str | tuple[str, str]]],
    filename: str,
    reftime: int,
    expected_result: Mapping[str, Sequence[str | tuple[str, str]]],
) -> None:
    result = fileinfo_groups_get_group_name(group_patterns, filename, reftime)
    assert result == expected_result


@pytest.mark.parametrize(
    "group_patterns, filename, reftime, expected_result",
    [
        (
            [("name %s", "~filename*")],
            "filename_aa",
            123456,
            {"name": ["~filename*"]},
        ),
    ],
)
def test_fileinfo_groups_get_group_name_error(
    group_patterns: list[tuple[str, str | tuple[str, str]]],
    filename: str,
    reftime: int,
    expected_result: Mapping[str, Sequence[str]],
) -> None:
    with pytest.raises(RuntimeError) as e:
        fileinfo_groups_get_group_name(group_patterns, filename, reftime)

    message = f"Invalid entry in inventory_fileinfo_groups: group name '{group_patterns[0][0]}' contains 1 times '%s', but regular expression '{group_patterns[0][1]}' contains only 0 subexpression(s)."

    assert e.value.args[0] == message


@pytest.mark.parametrize(
    "file_stat, reftime, params, expected_result",
    [
        (
            FileinfoItem(
                name="z:\\working\\client\\todo\\BP-15f86cb7-89d7-41a9-8aec-04b9e179f0b4.xml",
                missing=False,
                failed=False,
                size=539,
                time=None,
            ),
            123456,
            {},
            [Result(state=State.WARN, summary="File stat time failed")],
        ),
        (
            FileinfoItem(
                name="z:\\working\\client\\todo\\BP-15f86cb7-89d7-41a9-8aec-04b9e179f0b4.xml",
                missing=True,
                failed=False,
                size=539,
                time=1189173868,
            ),
            123456,
            {},
            [Result(state=State.UNKNOWN, summary="File not found")],
        ),
        (
            FileinfoItem(
                name="z:\\working\\client\\todo\\BP-15f86cb7-89d7-41a9-8aec-04b9e179f0b4.xml",
                missing=False,
                failed=False,
                size=539,
                time=1189173868,
            ),
            1189181234,
            {},
            [
                Result(state=State.OK, summary="Size: 539 B"),
                Metric("size", 539.0),
                Result(state=State.OK, summary="Age: 2 hours 2 minutes"),
                Metric("age", 7366.0),
            ],
        ),
        (
            FileinfoItem(
                name="/home/tim/test.txt", missing=True, failed=False, size=None, time=None
            ),
            1653985037,
            {"state_missing": 2},
            [Result(state=State.CRIT, summary="File not found")],
        ),
        (
            FileinfoItem(
                name="/home/tim/test.txt", missing=True, failed=False, size=None, time=None
            ),
            1653985037,
            {},
            [Result(state=State.UNKNOWN, summary="File not found")],
        ),
    ],
)
@time_machine.travel("2021-07-12 12:00")
def test_check_fileinfo_data(
    file_stat: FileinfoItem, reftime: int, params: dict[str, Any], expected_result: CheckResult
) -> None:
    result = list(check_fileinfo_data(file_stat, reftime, params))

    assert result == expected_result


@pytest.mark.parametrize(
    "filename, reftime, inclusion, exclusion, expected_result",
    [
        (
            "filename123",
            1189173868,
            "~file",
            "",
            (True, ""),
        ),
        (
            "filename123",
            1189173868,
            "",
            "~file",
            (False, ""),
        ),
    ],
)
def test__filename_matches(
    filename: str, reftime: int, inclusion: str, exclusion: str, expected_result: tuple[bool, str]
) -> None:
    result = _filename_matches(filename, reftime, inclusion, exclusion)
    assert result == expected_result


@pytest.mark.parametrize(
    "item, params, parsed, expected_result",
    [
        pytest.param(
            "my_folder/filename123",
            {"group_patterns": [("~my_folder/file.*", "")]},
            Fileinfo(
                reftime=1563288717,
                files={
                    "my_folder/filename123": FileinfoItem(
                        name="my_folder/filename123",
                        missing=True,
                        failed=False,
                        size=348,
                        time=1465079135,
                    ),
                    "my_folder/filename456": FileinfoItem(
                        name="my_folder/filename456",
                        missing=False,
                        failed=False,
                        size=348,
                        time=1465079135,
                    ),
                },
            ),
            [
                Result(state=State.OK, notice="Include patterns: ~my_folder/file.*"),
                Result(
                    state=State.OK,
                    notice="[my_folder/filename456] Age: 3 years 41 days, Size: 348 B",
                ),
                Result(state=State.OK, summary="Count: 1"),
                Metric("count", 1),
                Result(state=State.OK, summary="Size: 348 B"),
                Metric("size", 348),
                Result(state=State.OK, summary="Largest size: 348 B"),
                Metric("size_largest", 348),
                Result(state=State.OK, summary="Smallest size: 348 B"),
                Metric("size_smallest", 348),
                Result(state=State.OK, summary="Oldest age: 3 years 41 days"),
                Metric("age_oldest", 98209582),
                Result(state=State.OK, summary="Newest age: 3 years 41 days"),
                Metric("age_newest", 98209582),
            ],
            id="missing file",
        ),
        pytest.param(
            "my_folder/filename123",
            {"group_patterns": [("~my_folder/file.*", "")]},
            Fileinfo(
                reftime=1563288717,
                files={
                    "my_folder/filename123": FileinfoItem(
                        name="my_folder/filename123",
                        missing=False,
                        failed=True,
                        size=348,
                        time=1465079135,
                    ),
                    "my_folder/filename456": FileinfoItem(
                        name="my_folder/filename456",
                        missing=False,
                        failed=False,
                        size=348,
                        time=1465079135,
                    ),
                },
            ),
            [
                Result(state=State.OK, notice="Include patterns: ~my_folder/file.*"),
                Result(
                    state=State.OK,
                    notice="[my_folder/filename456] Age: 3 years 41 days, Size: 348 B",
                ),
                Result(state=State.WARN, summary="Files with unknown stat: my_folder/filename123"),
                Result(state=State.OK, summary="Count: 1"),
                Metric("count", 1),
                Result(state=State.OK, summary="Size: 348 B"),
                Metric("size", 348),
                Result(state=State.OK, summary="Largest size: 348 B"),
                Metric("size_largest", 348),
                Result(state=State.OK, summary="Smallest size: 348 B"),
                Metric("size_smallest", 348),
                Result(state=State.OK, summary="Oldest age: 3 years 41 days"),
                Metric("age_oldest", 98209582),
                Result(state=State.OK, summary="Newest age: 3 years 41 days"),
                Metric("age_newest", 98209582),
            ],
            id="failed file",
        ),
        pytest.param(
            "my_folder/*.dat",
            {
                "group_patterns": [("~my_folder/*.dat", "")],
                "conjunctions": [(2, [("age_oldest_lower", 129600)])],
                "maxcount": (10, 20),
            },
            Fileinfo(
                reftime=1563288717,
                files={
                    "my_folder/*.dat": FileinfoItem(
                        name="my_folder/*.dat",
                        missing=True,  # no files found
                        failed=True,
                        size=None,
                        time=1563288717,
                    ),
                },
            ),
            [
                Result(state=State.OK, notice="Include patterns: ~my_folder/*.dat"),
                Result(state=State.OK, summary="Count: 0"),
                Metric("count", 0.0, levels=(10.0, 20.0)),
                Result(state=State.OK, summary="Size: 0 B"),
                Metric("size", 0),
            ],
            id="test no matching pattern for conjunction",
        ),
        pytest.param(
            "my_folder/filename123",
            {"group_patterns": [("~my_folder/file.*", "")]},
            Fileinfo(
                reftime=1563288717,
                files={
                    "my_folder/filename456": FileinfoItem(
                        name="my_folder/filename456",
                        missing=False,
                        failed=False,
                        size=348,
                        time=1563288817,
                    ),
                },
            ),
            [
                Result(state=State.OK, notice="Include patterns: ~my_folder/file.*"),
                Result(
                    state=State.UNKNOWN,
                    summary="[my_folder/filename456] Age: -1 minute 40 seconds, Size: 348 B, The timestamp of the file is in the future. Please investigate your host times",
                ),
                Result(state=State.OK, summary="Count: 1"),
                Metric("count", 1),
                Result(state=State.OK, summary="Size: 348 B"),
                Metric("size", 348),
                Result(state=State.OK, summary="Largest size: 348 B"),
                Metric("size_largest", 348),
                Result(state=State.OK, summary="Smallest size: 348 B"),
                Metric("size_smallest", 348),
                Result(
                    state=State.UNKNOWN,
                    summary="Oldest age: -1 minute 40 seconds, The timestamp of the file is in the future. Please investigate your host times",
                ),
                Metric("age_oldest", -100.0),
                Result(
                    state=State.UNKNOWN,
                    summary="Newest age: -1 minute 40 seconds, The timestamp of the file is in the future. Please investigate your host times",
                ),
                Metric("age_newest", -100.0),
            ],
            id="negative age",
        ),
        pytest.param(
            "my_folder/filename123",
            {"group_patterns": [("~my_folder/file.*", "")], "negative_age_tolerance": 150},
            Fileinfo(
                reftime=1563288717,
                files={
                    "my_folder/filename456": FileinfoItem(
                        name="my_folder/filename456",
                        missing=False,
                        failed=False,
                        size=348,
                        time=1563288817,
                    ),
                },
            ),
            [
                Result(state=State.OK, notice="Include patterns: ~my_folder/file.*"),
                Result(
                    state=State.OK, notice="[my_folder/filename456] Age: 0 seconds, Size: 348 B"
                ),
                Result(state=State.OK, summary="Count: 1"),
                Metric("count", 1),
                Result(state=State.OK, summary="Size: 348 B"),
                Metric("size", 348),
                Result(state=State.OK, summary="Largest size: 348 B"),
                Metric("size_largest", 348),
                Result(state=State.OK, summary="Smallest size: 348 B"),
                Metric("size_smallest", 348),
                Result(
                    state=State.OK,
                    summary="Oldest age: 0 seconds",
                ),
                Metric("age_oldest", 0.0),
                Result(
                    state=State.OK,
                    summary="Newest age: 0 seconds",
                ),
                Metric("age_newest", 0.0),
            ],
            id="negative age within tolerance",
        ),
    ],
)
def test_check_fileinfo_groups_data(
    item: str,
    params: Mapping[str, object],
    parsed: Fileinfo,
    expected_result: Sequence[Result | Metric],
) -> None:
    reftime = parsed.reftime

    assert isinstance(reftime, int)

    result = list(check_fileinfo_groups_data(item, params, parsed, reftime))
    assert result == expected_result


@pytest.mark.parametrize(
    "check_definition, params, expected_result",
    [
        pytest.param(
            [
                MetricInfo("Size", "size", 7, render.filesize),
                MetricInfo("Age", "age", 3, render.timespan),
            ],
            {},
            [
                Result(state=State.OK, summary="Size: 7 B"),
                Metric("size", 7),
                Result(state=State.OK, summary="Age: 3 seconds"),
                Metric("age", 3),
            ],
            id="age and size",
        ),
        pytest.param(
            [
                MetricInfo("Age", "age", -30, render.timespan),
            ],
            {},
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Age: -30 seconds, The timestamp of the file is in the future. Please investigate your host times",
                ),
                Metric("age", -30.0),
            ],
            id="negative age",
        ),
        pytest.param(
            [
                MetricInfo("Age", "age", -3, render.timespan),
            ],
            {"negative_age_tolerance": 5},
            [
                Result(
                    state=State.OK,
                    summary="Age: 0 seconds",
                ),
                Metric("age", 0.0),
            ],
            id="negative age within tolerance",
        ),
    ],
)
def test__fileinfo_check_function(
    check_definition: list[MetricInfo], params: Mapping[str, object], expected_result: CheckResult
) -> None:
    result = list(_fileinfo_check_function(check_definition, params))
    assert result == expected_result


@pytest.mark.parametrize(
    "check_definition, params, expected_result",
    [
        (
            [
                ("Size", "size", 17, render.filesize),
                ("Newest age", "newest_age", 3, render.timespan),
            ],
            {"conjunctions": [(2, [("size", 12), ("newest_age_lower", 86400)])]},
            [
                Result(
                    state=State.CRIT,
                    summary="Conjunction: size at 12 B AND newest age below 1 day 0 hours",
                )
            ],
        ),
    ],
)
def test__fileinfo_check_conjunctions(
    check_definition: list[MetricInfo], params: Mapping[str, object], expected_result: CheckResult
) -> None:
    result = list(_fileinfo_check_conjunctions(check_definition, params))
    assert result == expected_result


@pytest.fixture(name="local2gmtime")
def _set_local2gmtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "localtime", time.gmtime)


def test_fileinfo_process_date_both_macros_replaced(local2gmtime: None) -> None:
    assert (
        fileinfo_process_date(r"\\hi\there\($DATE:%Y$|$YESTERDAY:%Y$).log", 0)
        == r"\\hi\there\(1970|1969).log"
    )


def test_fileinfo_process_date_multiple_occurances_replaced(local2gmtime: None) -> None:
    assert fileinfo_process_date(r"$DATE:%w$.$DATE:%Y$", -17502393600) == "3.1415"
