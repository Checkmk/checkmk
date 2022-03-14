#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
from freezegun import freeze_time

from cmk.base.check_api import get_age_human_readable, get_filesize_human_readable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
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
    fileinfo_check_timeranges,
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
def test__cast_value(value, cast_type):
    cast_value = _cast_value(value, cast_type)
    assert cast_value is None


def test__get_field():
    my_list = [1, 2, 3]
    field_value = _get_field(my_list, 3)
    assert field_value is None


def test__parse_single_legacy_row():
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
def test_parse_fileinfo(info, expected_result):
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
def test_fileinfo_groups_get_group_name(group_patterns, filename, reftime, expected_result):
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
def test_fileinfo_groups_get_group_name_error(group_patterns, filename, reftime, expected_result):
    with pytest.raises(RuntimeError) as e:
        fileinfo_groups_get_group_name(group_patterns, filename, reftime)

    message = f"Invalid entry in inventory_fileinfo_groups: group name '{group_patterns[0][0]}' contains 1 times '%s', but regular expression '{group_patterns[0][1]}' contains only 0 subexpression(s)."

    assert e.value.args[0] == message


@pytest.mark.parametrize(
    "params, expected_result",
    [
        (
            {"timeofday": [((8, 0), (17, 0))]},
            "",
        ),
        (
            {"timeofday": [((8, 0), (9, 0))]},
            "Out of relevant time of day",
        ),
    ],
)
@freeze_time("2021-07-12 12:00")
def test_fileinfo_check_timeranges(params, expected_result):
    result = fileinfo_check_timeranges(params)

    assert result == expected_result


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
            {"timeofday": [((8, 0), (9, 0))]},
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
            {"timeofday": [((8, 0), (9, 0))]},
            [Result(state=State.OK, summary="File not found - Out of relevant time of day")],
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
            {"timeofday": [((8, 0), (9, 0))]},
            [
                Result(state=State.OK, summary="Size: 539 B"),
                Metric("size", 539.0),
                Result(state=State.OK, summary="Age: 2 hours 2 minutes"),
                Metric("age", 7366.0),
                Result(state=State.OK, summary="Out of relevant time of day"),
            ],
        ),
    ],
)
@freeze_time("2021-07-12 12:00")
def test_check_fileinfo_data(file_stat, reftime, params, expected_result):
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
def test__filename_matches(filename, reftime, inclusion, exclusion, expected_result):
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
    ],
)
def test_check_fileinfo_groups_data(item, params, parsed, expected_result):
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
                Result(state=State.OK, summary="Age: 3.00 s"),
                Metric("age", 3),
            ],
        )
    ],
)
def test__fileinfo_check_function(check_definition, params, expected_result):
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
                    state=State.CRIT, summary="Conjunction: size at 12 B AND newest age below 24 h"
                )
            ],
        )
    ],
)
def test__fileinfo_check_conjunctions(check_definition, params, expected_result):
    result = list(_fileinfo_check_conjunctions(check_definition, params))
    assert result == expected_result
