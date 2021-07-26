#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
import collections
from tests.testlib import on_time, Check

from tests.unit.checks.checktestlib import MockHostExtraConf
from cmk.base.check_legacy_includes.fileinfo import (
    _cast_value,
    _get_field,
    _parse_single_legacy_row,
    parse_fileinfo,
    fileinfo_groups_get_group_name,
    fileinfo_check_timeranges,
    check_fileinfo_data,
    _filename_matches,
    _define_fileinfo_group_check,
    check_fileinfo_groups_data,
    _fileinfo_check_function,
    _fileinfo_check_conjunctions,
)
from cmk.base.check_api import get_filesize_human_readable, get_age_human_readable
from cmk.utils.type_defs import CheckPluginName
from cmk.utils.exceptions import MKGeneralException

pytestmark = pytest.mark.checks

FileinfoItem = collections.namedtuple("FileinfoItem", "name missing failed size time")


@pytest.mark.parametrize("value, cast_type", [
    (None, float),
    ("some string", int),
])
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


@pytest.mark.parametrize("info, expected_result", [
    ([
        ["1415625919"],
        ["string"],
        ["C:\\Datentransfer\\ORU\\KC\\dummy.txt", "1917", "1189173868"],
        ["C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7", "2414", "1415625918"],
        ["C:\\Datentransfer\\ORU\\KC\\KC_41135.sem", "1", "1415625918"],
    ], {
        "files": {
            "C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7": FileinfoItem(
                name="C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7",
                missing=False,
                failed=False,
                size=2414,
                time=1415625918),
            "C:\\Datentransfer\\ORU\\KC\\KC_41135.sem": FileinfoItem(
                name="C:\\Datentransfer\\ORU\\KC\\KC_41135.sem",
                missing=False,
                failed=False,
                size=1,
                time=1415625918),
            "C:\\Datentransfer\\ORU\\KC\\dummy.txt": FileinfoItem(
                name="C:\\Datentransfer\\ORU\\KC\\dummy.txt",
                missing=False,
                failed=False,
                size=1917,
                time=1189173868)
        },
        "reftime": 1415625919
    }),
    ([
        ["1415625919"],
        ["No such file or directory", 4, 5],
        ["C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7", "2414", "1415625918"],
        ["C:\\Datentransfer\\ORU\\KC\\KC_41135.sem", "1", "1415625918"],
    ], {
        "files": {
            "C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7": FileinfoItem(
                name="C:\\Datentransfer\\ORU\\KC\\KC_41135.hl7",
                missing=False,
                failed=False,
                size=2414,
                time=1415625918),
            "C:\\Datentransfer\\ORU\\KC\\KC_41135.sem": FileinfoItem(
                name="C:\\Datentransfer\\ORU\\KC\\KC_41135.sem",
                missing=False,
                failed=False,
                size=1,
                time=1415625918)
        },
        "reftime": 1415625919
    }),
])
def test_parse_fileinfo(info, expected_result):
    assert parse_fileinfo(info) == expected_result


@pytest.mark.parametrize("group_patterns, filename, reftime, expected_result", [
    (
        [("name", "~filename*")],
        "filename_aa",
        123456,
        {
            'name': ['~filename*']
        },
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
        {
            'name': [('~~file', '')]
        },
    ),
])
def test_fileinfo_groups_get_group_name(group_patterns, filename, reftime, expected_result):
    result = fileinfo_groups_get_group_name(group_patterns, filename, reftime)
    assert result == expected_result


@pytest.mark.parametrize("group_patterns, filename, reftime, expected_result", [
    (
        [("name %s", "~filename*")],
        "filename_aa",
        123456,
        {
            'name': ['~filename*']
        },
    ),
])
def test_fileinfo_groups_get_group_name_error(group_patterns, filename, reftime, expected_result):
    with pytest.raises(MKGeneralException) as e:
        fileinfo_groups_get_group_name(group_patterns, filename, reftime)

    message = f"Invalid entry in inventory_fileinfo_groups: group name '{group_patterns[0][0]}' contains 1 times '%s', but regular expression '{group_patterns[0][1]}' contains only 0 subexpression(s)."

    assert e.value.args[0] == message


@pytest.mark.parametrize("params, expected_result", [
    (
        {
            "timeofday": [((8, 0), (17, 0))]
        },
        "",
    ),
    (
        {
            "timeofday": [((8, 0), (9, 0))]
        },
        "Out of relevant time of day",
    ),
])
def test_fileinfo_check_timeranges(params, expected_result):
    with on_time('2021-07-12 12:00', 'CET'):
        result = fileinfo_check_timeranges(params)

    assert result == expected_result


@pytest.mark.parametrize("file_stat, reftime, params, expected_result", [
    (
        FileinfoItem(name='z:\\working\\client\\todo\\BP-15f86cb7-89d7-41a9-8aec-04b9e179f0b4.xml',
                     missing=False,
                     failed=False,
                     size=539,
                     time=None),
        123456,
        {
            "timeofday": [((8, 0), (9, 0))]
        },
        [1, 'File stat time failed'],
    ),
    (
        FileinfoItem(name='z:\\working\\client\\todo\\BP-15f86cb7-89d7-41a9-8aec-04b9e179f0b4.xml',
                     missing=True,
                     failed=False,
                     size=539,
                     time=1189173868),
        123456,
        {
            "timeofday": [((8, 0), (9, 0))]
        },
        [0, 'File not found - Out of relevant time of day'],
    ),
])
def test_check_fileinfo_data(file_stat, reftime, params, expected_result):
    with on_time('2021-07-12 12:00', 'CET'):
        result = list(check_fileinfo_data(file_stat, reftime, params))

    assert result == expected_result


@pytest.mark.parametrize("filename, reftime, inclusion, exclusion, expected_result", [
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
])
def test__filename_matches(filename, reftime, inclusion, exclusion, expected_result):
    result = _filename_matches(filename, reftime, inclusion, exclusion)
    assert result == expected_result


@pytest.mark.parametrize("item, params, parsed, expected_result", [
    (
        "my_folder/filename123",
        {
            'group_patterns': [('~my_folder/file.*', '')]
        },
        {
            'reftime': 1563288717,
            'files': {
                'my_folder/filename123': FileinfoItem(name='my_folder/filename123',
                                                      missing=True,
                                                      failed=False,
                                                      size=348,
                                                      time=1465079135),
                'my_folder/filename456': FileinfoItem(name='my_folder/filename456',
                                                      missing=False,
                                                      failed=False,
                                                      size=348,
                                                      time=1465079135),
            }
        },
        [
            (0, 'Count: 1', [('count', 1, None, None)]),
            (0, 'Size: 348 B', [('size', 348, None, None)]),
            (0, 'Largest size: 348 B', [('size_largest', 348, None, None)]),
            (0, 'Smallest size: 348 B', [('size_smallest', 348, None, None)]),
            (0, 'Oldest age: 3.1 y', [('age_oldest', 98209582, None, None)]),
            (0, 'Newest age: 3.1 y', [('age_newest', 98209582, None, None)]),
            (0, '\n'
             'Include patterns: ~my_folder/file.*\n'
             '[my_folder/filename456] Age: 3.1 y, Size: 348 B'),
        ],
    ),
    ("my_folder/filename123", {
        'group_patterns': [('~my_folder/file.*', '')]
    }, {
        'reftime': 1563288717,
        'files': {
            'my_folder/filename123': FileinfoItem(
                name='my_folder/filename123', missing=False, failed=True, size=348,
                time=1465079135),
            'my_folder/filename456': FileinfoItem(name='my_folder/filename456',
                                                  missing=False,
                                                  failed=False,
                                                  size=348,
                                                  time=1465079135),
        }
    }, [
        (1, 'Files with unknown stat: my_folder/filename123'),
        (0, 'Count: 1', [('count', 1, None, None)]),
        (0, 'Size: 348 B', [('size', 348, None, None)]),
        (0, 'Largest size: 348 B', [('size_largest', 348, None, None)]),
        (0, 'Smallest size: 348 B', [('size_smallest', 348, None, None)]),
        (0, 'Oldest age: 3.1 y', [('age_oldest', 98209582, None, None)]),
        (0, 'Newest age: 3.1 y', [('age_newest', 98209582, None, None)]),
        (0, '\n'
         'Include patterns: ~my_folder/file.*\n'
         '[my_folder/filename456] Age: 3.1 y, Size: 348 B'),
    ]),
])
@pytest.mark.usefixtures("fix_register")
def test_check_fileinfo_groups_data(item, params, parsed, expected_result):
    fileinfo_groups_check = Check('fileinfo.groups')

    def mock_host_extra_conf(_hostname, _rulesets):
        return []

    with MockHostExtraConf(fileinfo_groups_check, mock_host_extra_conf, 'host_extra_conf'):
        result = list(check_fileinfo_groups_data(item, params, parsed, parsed['reftime']))
    assert result == expected_result


@pytest.mark.parametrize("check_definition, params, expected_result", [(
    [
        ("Size", "size", 7, get_filesize_human_readable),
        ("Age", "age", 3, get_age_human_readable),
    ],
    {},
    [
        (0, 'Out of range', []),
        (0, 'Size: 7 B', [('size', 7, None, None)]),
        (0, 'Age: 3.00 s', [('age', 3, None, None)]),
    ],
)])
def test__fileinfo_check_function(check_definition, params, expected_result):
    result = list(_fileinfo_check_function(check_definition, params, "Out of range"))
    assert result == expected_result


@pytest.mark.parametrize("check_definition, params, expected_result", [(
    [
        ("Size", "size", 17, get_filesize_human_readable),
        ("Newest age", "newest_age", 3, get_age_human_readable),
    ],
    {
        "conjunctions": [(2, [('size', 12), ('newest_age_lower', 86400)])]
    },
    [(2, 'Conjunction: size at 12 B AND newest age below 24 h')],
)])
def test__fileinfo_check_conjunctions(check_definition, params, expected_result):
    result = list(_fileinfo_check_conjunctions(check_definition, params))
    assert result == expected_result
