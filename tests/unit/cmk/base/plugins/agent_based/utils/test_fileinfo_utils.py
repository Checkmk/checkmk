#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest
from freezegun import freeze_time

from cmk.base.check_api import get_age_human_readable, get_filesize_human_readable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.utils.fileinfo import (
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
    FileinfoItem,
    MetricInfo,
    parse_fileinfo,
)

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "value, cast_type",
    [
        (None, float),
        ("some string", int),
    ],
)
def test__cast_value(value, cast_type) -> None:  # type:ignore[no-untyped-def]
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
def test_parse_fileinfo(info, expected_result) -> None:  # type:ignore[no-untyped-def]
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
def test_fileinfo_groups_get_group_name(  # type:ignore[no-untyped-def]
    group_patterns, filename, reftime, expected_result
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
def test_fileinfo_groups_get_group_name_error(  # type:ignore[no-untyped-def]
    group_patterns, filename, reftime, expected_result
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
@freeze_time("2021-07-12 12:00")
def test_check_fileinfo_data(  # type:ignore[no-untyped-def]
    file_stat: FileinfoItem, reftime: int, params: dict[str, Any], expected_result: CheckResult
):
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
def test__filename_matches(  # type:ignore[no-untyped-def]
    filename, reftime, inclusion, exclusion, expected_result
) -> None:
    result = _filename_matches(filename, reftime, inclusion, exclusion)
    assert result == expected_result


@pytest.mark.parametrize(
    "item, params, parsed, expected_result",
    [
        (
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
        ),
        (
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
    ],
)
def test_check_fileinfo_groups_data(  # type:ignore[no-untyped-def]
    item, params, parsed, expected_result
) -> None:
    result = list(check_fileinfo_groups_data(item, params, parsed, parsed.reftime))
    assert result == expected_result


@pytest.mark.parametrize(
    "check_definition, params, expected_result",
    [
        (
            [
                MetricInfo("Size", "size", 7, get_filesize_human_readable),
                MetricInfo("Age", "age", 3, get_age_human_readable),
            ],
            {},
            [
                Result(state=State.OK, summary="Size: 7 B"),
                Metric("size", 7),
                Result(state=State.OK, summary="Age: 3 seconds"),
                Metric("age", 3),
            ],
        )
    ],
)
def test__fileinfo_check_function(  # type:ignore[no-untyped-def]
    check_definition, params, expected_result
) -> None:
    result = list(_fileinfo_check_function(check_definition, params))
    assert result == expected_result


@pytest.mark.parametrize(
    "check_definition, params, expected_result",
    [
        (
            [
                ("Size", "size", 17, get_filesize_human_readable),
                ("Newest age", "newest_age", 3, get_age_human_readable),
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
def test__fileinfo_check_conjunctions(  # type:ignore[no-untyped-def]
    check_definition, params, expected_result
) -> None:
    result = list(_fileinfo_check_conjunctions(check_definition, params))
    assert result == expected_result
