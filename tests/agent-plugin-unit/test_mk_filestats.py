#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import configparser

# pylint: disable=protected-access,redefined-outer-name
import os
import sys

import pytest

import agents.plugins.mk_filestats as mk_filestats

try:
    from collections import OrderedDict
except ImportError:  # Python2
    from ordereddict import OrderedDict  # type: ignore


def configparser_library_name():
    python_version = sys.version_info
    if python_version[0] == 2 and python_version[1] < 7:
        # the configparser library is named ConfigParser in Python 2.6 and below.
        # its name is replaced by the 3to2 tool automatically in-code, but
        # obviously the strings are not replaced
        return "ConfigParser"
    return "configparser"


@pytest.fixture
def lazyfile():
    mylazyfile = mk_filestats.FileStat(__file__)

    # Overwrite the path to be reproducable...
    mylazyfile.path = "test_mk_filestats.py"
    return mylazyfile


def test_lazy_file():
    lfile = mk_filestats.FileStat("/bla/no such file.txt")
    assert lfile.path == "/bla/no such file.txt"
    assert lfile.size is None
    assert lfile.age is None
    assert lfile.stat_status == "file vanished"

    lfile = mk_filestats.FileStat(__file__)  # this should exist...
    assert lfile.path == __file__
    assert lfile.size == os.stat(__file__).st_size
    assert lfile.stat_status == "ok"
    assert isinstance(lfile.age, int)
    assert isinstance(ast.literal_eval(lfile.dumps()), dict)


@pytest.mark.parametrize(
    "config", [({}), ({"input_unknown": None}), ({"input_one": None, "input_two": None})]
)
def test_get_file_iterator_invalid(config):
    with pytest.raises(ValueError):
        mk_filestats.get_file_iterator(config)


@pytest.mark.parametrize(
    "config,pat_list",
    [
        ({"input_patterns": "foo"}, ["foo"]),
        ({"input_patterns": '"foo bar" gee*'}, ["foo bar", "gee*"]),
    ],
)
def test_get_file_iterator_pattern(config, pat_list):
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
def test_numeric_filter(operator, values, results):
    num_filter = mk_filestats.AbstractNumericFilter("%s1024" % operator)
    for value, result in zip(values, results):
        assert result == num_filter._matches_value(value)


@pytest.mark.parametrize("invalid_arg", ["<>1024", "<NaN"])
def test_numeric_filter_raises(invalid_arg):
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
def test_path_filter(reg_pat, paths, results):
    path_filter = mk_filestats.RegexFilter(reg_pat)
    for path, result in zip(paths, results):
        lazy_file = mk_filestats.FileStat(path)
        assert result == path_filter.matches(lazy_file)


@pytest.mark.parametrize(
    "config",
    [
        {"filter_foo": None},
        {"filter_size": "!=käse"},
    ],
)
def test_get_file_filters_invalid(config):
    with pytest.raises(ValueError):
        mk_filestats.get_file_filters(config)


def test_get_file_filters():
    config = {"filter_size": ">1", "filter_age": "==0", "filter_regex": "foo"}
    filters = mk_filestats.get_file_filters(config)
    assert len(filters) == 3
    assert isinstance(filters[0], mk_filestats.RegexFilter)
    assert isinstance(filters[1], mk_filestats.AbstractNumericFilter)
    assert isinstance(filters[2], mk_filestats.AbstractNumericFilter)


@pytest.mark.parametrize("config", [{}, {"output": "/dev/null"}])
def test_get_ouput_aggregator_invalid(config):
    with pytest.raises(ValueError):
        mk_filestats.get_output_aggregator(config)


@pytest.mark.parametrize("output_value", ["count_only", "file_stats", "single_file"])
def test_get_ouput_aggregator(output_value):
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
def test_output_aggregator_single_file_servicename(lazyfile, group_name, expected):

    actual = mk_filestats.output_aggregator_single_file(group_name, [lazyfile])
    assert expected == list(actual)[0]


class MockConfigParser(configparser.RawConfigParser):
    def read(self, cfg_file):  # pylint:disable=arguments-differ
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
            configparser_library_name() + ".ConfigParser",
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


class MockedFileStatFile:
    def __init__(self, path):
        self.path = path

    def __eq__(self, other):
        return self.path == other.path


@pytest.mark.parametrize(
    "section_name, files_iter, grouping_conditions, expected_result",
    [
        (
            "banana",
            iter(
                [
                    MockedFileStatFile("/var/log/syslog"),
                    MockedFileStatFile("/var/log/syslog1"),
                    MockedFileStatFile("/var/log/syslog2"),
                    MockedFileStatFile("/var/log/apport"),
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
                    [MockedFileStatFile("/var/log/syslog1")],
                ),
                (
                    "banana colibri",
                    [
                        MockedFileStatFile("/var/log/syslog"),
                        MockedFileStatFile("/var/log/syslog2"),
                    ],
                ),
                (
                    "banana",
                    [MockedFileStatFile("/var/log/apport")],
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
            assert single_file == expected_results_list[results_idx][1][files_idx]
