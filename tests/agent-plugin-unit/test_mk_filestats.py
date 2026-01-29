#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# ruff: noqa: RUF100
# ruff: noqa: I001

import ast
import configparser
import os
import sys
from collections import OrderedDict
from typing import Mapping, Optional, Sequence, Tuple

import pytest
from agents.plugins import mk_filestats

MYLAZYFILE = mk_filestats.FileStat.from_path(__file__, __file__)
# Overwrite the path to be reproducable...
MYLAZYFILE.file_path = mk_filestats.ensure_str("test_mk_filestats.py")
MYLAZYFILE.regex_matchable_path = mk_filestats.ensure_str("test_mk_filestats.py")


def test_lazy_file() -> None:
    lfile = mk_filestats.FileStat.from_path("/bla/no such file.txt", "/bla/no such file.txt")
    assert lfile.file_path == "/bla/no such file.txt"
    assert lfile.size is None
    assert lfile.age is None
    assert lfile.stat_status == "file vanished"

    lfile = mk_filestats.FileStat.from_path(__file__, __file__)  # this should exist...
    assert lfile.file_path == __file__
    assert lfile.size == os.stat(__file__).st_size
    assert lfile.stat_status == "ok"
    assert isinstance(lfile.age, int)
    assert isinstance(ast.literal_eval(lfile.dumps()), dict)


@pytest.mark.parametrize(
    "config", [({}), ({"input_unknown": None}), ({"input_one": None, "input_two": None})]
)
def test_get_file_iterator_invalid(config: Mapping[str, Optional[str]]) -> None:
    with pytest.raises(ValueError):
        mk_filestats.get_file_iterator(config)


@pytest.mark.parametrize(
    "config,pat_list",
    [
        ({"input_patterns": "foo"}, ["foo"]),
        ({"input_patterns": '"foo bar" gee*'}, ["foo bar", "gee*"]),
    ],
)
def test_get_file_iterator_pattern(
    config: Mapping[str, Optional[str]], pat_list: Sequence[str]
) -> None:
    iter_obj = mk_filestats.get_file_iterator(config)
    assert isinstance(iter_obj, mk_filestats.PatternIterator)
    assert iter_obj._patterns == [os.path.abspath(p) for p in pat_list]


@pytest.mark.parametrize(
    "operator,values,results",
    [
        (">", (2000.0, 1024, "1000"), (True, False, False)),
        (">=", (2000.0, 1024, "1000"), (True, True, False)),
        ("<", (2000.0, 1024, "1000"), (False, False, True)),
        ("<=", (2000.0, 1024, "1000"), (False, True, True)),
        ("==", (2000.0, 1024, "1000"), (False, True, False)),
    ],
)
def test_numeric_filter(
    operator: str, values: Tuple[float, int, str], results: Tuple[bool, bool, bool]
) -> None:
    num_filter = mk_filestats.AbstractNumericFilter("%s1024" % operator)
    for value, result in zip(values, results):
        assert result == num_filter._matches_value(value)


@pytest.mark.parametrize("invalid_arg", ["<>1024", "<NaN"])
def test_numeric_filter_raises(invalid_arg: str) -> None:
    with pytest.raises(ValueError):
        mk_filestats.AbstractNumericFilter(invalid_arg)


@pytest.mark.parametrize(
    "reg_pat,paths,results",
    [
        (
            r".*\.txt",
            ("/path/to/some.txt", "to/sometxt", "/path/to/some.TXT"),
            (True, False, False),
        ),
        ("[^ð]*ð{2}[^ð]*", ("foðbar", "fððbar"), (False, True)),
    ],
)
def test_path_filter(reg_pat: str, paths: Sequence[str], results: Sequence[bool]) -> None:
    path_filter = mk_filestats.RegexFilter(reg_pat)
    for path, result in zip(paths, results):
        assert result == path_filter.matches(mk_filestats._sanitize_path(path))


@pytest.mark.parametrize(
    "config",
    [
        {"filter_foo": None},
        {"filter_size": "!=käse"},
    ],
)
def test_get_file_filters_invalid(config: Mapping[str, Optional[str]]) -> None:
    with pytest.raises(ValueError):
        mk_filestats.get_file_filters(config)


def test_get_file_filters() -> None:
    config = {"filter_size": ">1", "filter_age": "==0", "filter_regex": "foo"}
    filters = mk_filestats.get_file_filters(config)
    assert len(filters) == 3
    assert isinstance(filters[0], mk_filestats.RegexFilter)
    assert isinstance(filters[1], mk_filestats.AbstractNumericFilter)
    assert isinstance(filters[2], mk_filestats.AbstractNumericFilter)


@pytest.mark.parametrize("config", [{}, {"output": "/dev/null"}])
def test_get_ouput_aggregator_invalid(config: Mapping[str, str]) -> None:
    with pytest.raises(ValueError):
        mk_filestats.get_output_aggregator(config)


@pytest.mark.parametrize("output_value", ["count_only", "file_stats", "single_file"])
def test_get_ouput_aggregator(output_value: str) -> None:
    aggr = mk_filestats.get_output_aggregator({"output": output_value})
    assert aggr is getattr(mk_filestats, "output_aggregator_%s" % output_value)


@pytest.mark.parametrize(
    "group_name, expected",
    [
        ("myService", "[[[single_file myService]]]"),
        ("myservice %s", "[[[single_file myservice test_mk_filestats.py]]]"),
        ("myservice %s %s", "[[[single_file myservice test_mk_filestats.py %s]]]"),
        ("%s", "[[[single_file test_mk_filestats.py]]]"),
        ("%s %s", "[[[single_file test_mk_filestats.py %s]]]"),
        ("%s%s", "[[[single_file test_mk_filestats.py%s]]]"),
        ("%s%s %s %s", "[[[single_file test_mk_filestats.py%s %s %s]]]"),
        ("%s myService", "[[[single_file test_mk_filestats.py myService]]]"),
        ("%s myService %s", "[[[single_file test_mk_filestats.py myService %s]]]"),
    ],
)
def test_output_aggregator_single_file_servicename(group_name: str, expected: str) -> None:
    actual = mk_filestats.output_aggregator_single_file(group_name, [MYLAZYFILE])
    assert expected == list(actual)[0]


class MockConfigParser(configparser.RawConfigParser):
    def read(self, cfg_file):  # type: ignore[override]
        pass


class TestConfigParsing:
    @pytest.fixture
    def config_file_name(self):
        return "filestats.cfg"

    @pytest.fixture
    def config_options(self):
        return [
            ("banana", "input_patterns", "/home/banana/*"),
            ("banana@penguin", "grouping_regex", "/home/banana/penguin*"),
            ("banana@camel", "grouping_regex", "/home/banana/camel"),
            ("strawberry", "input_patterns", "/var/log/*"),
        ]

    @pytest.fixture
    def mocked_configparser(self, config_options):
        # FIXME: Python 2.6 has no OrderedDict at all, it is only available in a separate ordereddict
        # package, but we simply can't assume that this is installed on the client!
        parser = MockConfigParser(mk_filestats.DEFAULT_CFG_SECTION, dict_type=OrderedDict)
        for section, option, value in config_options:
            parser.add_section(section)
            parser.set(section, option, value)
        return parser

    def test_iter_config_section_dicts(
        self,
        config_file_name,
        mocked_configparser,
        mocker,
    ):
        mocker.patch(
            (
                "ConfigParser.ConfigParser"
                if sys.version_info[0] == 2
                else "configparser.ConfigParser"
            ),
            return_value=mocked_configparser,
        )
        actual_results = list(mk_filestats.iter_config_section_dicts(config_file_name))

        assert actual_results
        assert sorted([r[0] for r in actual_results]) == ["banana", "strawberry"]

        for _section, config_dict in [r for r in actual_results if r[0] == "banana"]:
            assert len(config_dict.items()) == 4
            assert config_dict["input_patterns"] == "/home/banana/*"
            assert config_dict["output"] == "file_stats"
            assert config_dict["subgroups_delimiter"] == "@"

            # test that the order is preserved
            assert config_dict["grouping"][0][0] == "penguin"
            assert config_dict["grouping"][1][0] == "camel"

            assert sorted(config_dict["grouping"][0][1].items()) == [
                ("rule", "/home/banana/penguin*"),
                ("type", "regex"),
            ]
            assert sorted(config_dict["grouping"][1][1].items()) == [
                ("rule", "/home/banana/camel"),
                ("type", "regex"),
            ]

        for _section, config_dict in [r for r in actual_results if r[0] == "strawberry"]:
            assert len(config_dict.items()) == 3
            assert config_dict["input_patterns"] == "/var/log/*"
            assert config_dict["output"] == "file_stats"
            assert config_dict["subgroups_delimiter"] == "@"


@pytest.mark.parametrize(
    "section_name, files_iter, grouping_conditions, expected_result",
    [
        (
            "banana",
            iter(
                [
                    mk_filestats.FileStat("/var/log/syslog", "ok"),
                    mk_filestats.FileStat("/var/log/syslog1", "ok"),
                    mk_filestats.FileStat("/var/log/syslog2", "ok"),
                    mk_filestats.FileStat("/var/log/apport", "ok"),
                ]
            ),
            [
                (
                    "raccoon",
                    {
                        "type": "regex",
                        "rule": "/var/log/syslog1",
                    },
                ),
                (
                    "colibri",
                    {
                        "type": "regex",
                        "rule": "/var/log/sys*",
                    },
                ),
            ],
            [
                (
                    "banana raccoon",
                    [mk_filestats.FileStat("/var/log/syslog1", "ok")],
                ),
                (
                    "banana colibri",
                    [
                        mk_filestats.FileStat("/var/log/syslog", "ok"),
                        mk_filestats.FileStat("/var/log/syslog2", "ok"),
                    ],
                ),
                (
                    "banana",
                    [mk_filestats.FileStat("/var/log/apport", "ok")],
                ),
            ],
        ),
        (
            "no_files",
            iter([]),
            [
                (
                    "raccoon",
                    {
                        "type": "regex",
                        "rule": "/var/log/syslog1",
                    },
                ),
                (
                    "colibri",
                    {
                        "type": "regex",
                        "rule": "/var/log/sys*",
                    },
                ),
            ],
            [
                ("no_files", []),
                ("no_files raccoon", []),
                ("no_files colibri", []),
            ],
        ),
    ],
)
def test_grouping_multiple_groups(
    section_name,
    files_iter,
    grouping_conditions,
    expected_result,
):
    results_list = sorted(
        mk_filestats.grouping_multiple_groups(
            section_name,
            files_iter,
            grouping_conditions=grouping_conditions,
        )
    )
    expected_results_list = sorted(expected_result)
    for results_idx, (
        section_name_arg,
        files,
    ) in enumerate(results_list):
        assert section_name_arg == expected_results_list[results_idx][0]
        for files_idx, single_file in enumerate(files):
            assert (
                single_file.file_path == expected_results_list[results_idx][1][files_idx].file_path
            )


@pytest.mark.parametrize("val", [None, "null"])
def test_explicit_null_in_filestat(val):
    filestat = mk_filestats.FileStat(
        file_path="hurz",
        stat_status="file vanished",
        size=val,
        age=val,
    )

    assert not mk_filestats.SizeFilter(">=1024").matches(filestat)
    assert not mk_filestats.AgeFilter(">=1024").matches(filestat)


@pytest.mark.parametrize(
    "files,expected_header,expected_dicts",
    [
        pytest.param(
            [
                mk_filestats.FileStat("/tmp/file1", "ok", 512, 600),
                mk_filestats.FileStat("/tmp/file2", "file_vanished"),
            ],
            "[[[extremes_only MYGROUP]]]",
            [
                {
                    "type": "file",
                    "path": "/tmp/file1",
                    "stat_status": "ok",
                    "size": 512,
                    "age": 600,
                    "mtime": None,
                },
                {"type": "summary", "count": 2},
            ],
            id="file without metrics",
        ),
        pytest.param(
            [
                mk_filestats.FileStat("/tmp/file1", "file_vanished"),
                mk_filestats.FileStat("/tmp/file2", "ok", 512, 600),
            ],
            "[[[extremes_only MYGROUP]]]",
            [
                {
                    "type": "file",
                    "path": "/tmp/file2",
                    "stat_status": "ok",
                    "size": 512,
                    "age": 600,
                    "mtime": None,
                },
                {"type": "summary", "count": 2},
            ],
            id="file without metrics is the first one",
        ),
        pytest.param(
            [
                mk_filestats.FileStat("/tmp/file1", "file_vanished"),
            ],
            "[[[extremes_only MYGROUP]]]",
            [
                {
                    "type": "file",
                    "path": "/tmp/file1",
                    "stat_status": "file_vanished",
                    "size": None,
                    "age": None,
                    "mtime": None,
                },
                {"type": "summary", "count": 1},
            ],
            id="only file without metrics",
        ),
    ],
)
def test_output_aggregator_extremes_only(files, expected_header, expected_dicts):
    result = list(mk_filestats.output_aggregator_extremes_only("MYGROUP", files))

    assert result[0] == expected_header
    for result_dict_repr, expected_dict in zip(result[1:], expected_dicts):
        assert ast.literal_eval(result_dict_repr) == expected_dict


_TEST_DIR_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "datasets",
        "mk_filestats",
    )
)


@pytest.mark.parametrize(
    ["pattern_list", "filters", "expected_result"],
    [
        pytest.param(
            [_TEST_DIR_PATH],
            [],
            [
                _TEST_DIR_PATH + "/testfile1.txt",
                _TEST_DIR_PATH + "/subdir/testfile2.html",
            ],
        ),
        pytest.param(
            [_TEST_DIR_PATH + "/*"],
            [],
            [
                _TEST_DIR_PATH + "/testfile1.txt",
                _TEST_DIR_PATH + "/subdir/testfile2.html",
            ],
        ),
        pytest.param(
            [_TEST_DIR_PATH],
            [mk_filestats.RegexFilter(".*html")],
            [
                _TEST_DIR_PATH + "/subdir/testfile2.html",
            ],
        ),
        pytest.param(
            [_TEST_DIR_PATH],
            [mk_filestats.RegexFilter(".*txt")],
            [
                _TEST_DIR_PATH + "/testfile1.txt",
            ],
        ),
        pytest.param(
            [_TEST_DIR_PATH],
            [
                mk_filestats.RegexFilter(".*testfile.*"),
                mk_filestats.InverseRegexFilter(".*html"),
            ],
            [
                _TEST_DIR_PATH + "/testfile1.txt",
            ],
        ),
        pytest.param(
            [_TEST_DIR_PATH + "/*"],
            [mk_filestats.RegexFilter(".*txt")],
            [
                _TEST_DIR_PATH + "/testfile1.txt",
            ],
        ),
        pytest.param(
            [_TEST_DIR_PATH + "/*"],
            [mk_filestats.RegexFilter(".*html")],
            [
                _TEST_DIR_PATH + "/subdir/testfile2.html",
            ],
        ),
        pytest.param(
            [_TEST_DIR_PATH + "/*"],
            [
                mk_filestats.RegexFilter(".*testfile.*"),
                mk_filestats.InverseRegexFilter(".*txt"),
            ],
            [
                _TEST_DIR_PATH + "/subdir/testfile2.html",
            ],
        ),
    ],
)
def test_pattern_iterator(pattern_list, filters, expected_result):
    assert sorted(
        file_stat.file_path
        for file_stat in mk_filestats.PatternIterator(
            pattern_list,
            filters,
        )
    ) == sorted(expected_result)
