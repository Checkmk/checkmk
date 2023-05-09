#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast

# pylint: disable=protected-access,redefined-outer-name
import os
import pytest  # type: ignore[import]
from utils import import_module

from collections import namedtuple


@pytest.fixture(scope="module")
def mk_filestats():
    return import_module("mk_filestats.py")


@pytest.fixture
def lazyfile(mk_filestats):
    mylazyfile = mk_filestats.FileStat(__file__)

    # Overwrite the path to be reproducable...
    mylazyfile.path = "test_mk_filestats.py"
    return mylazyfile


def test_lazy_file(mk_filestats):
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


@pytest.mark.parametrize("config", [({}), ({
    "input_unknown": None
}), ({
    "input_one": None,
    "input_two": None
})])
def test_get_file_iterator_invalid(mk_filestats, config):
    with pytest.raises(ValueError):
        mk_filestats.get_file_iterator(config)


@pytest.mark.parametrize(
    "config,pat_list",
    [
        ({
            "input_patterns": "foo"
        }, ["foo"]),
        ({
            "input_patterns": '"foo bar" gee*'
        }, ["foo bar", "gee*"]),
    ],
)
def test_get_file_iterator_pattern(mk_filestats, config, pat_list):
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
def test_numeric_filter(mk_filestats, operator, values, results):
    num_filter = mk_filestats.AbstractNumericFilter("%s1024" % operator)
    for value, result in zip(values, results):
        assert result == num_filter._matches_value(value)


@pytest.mark.parametrize("invalid_arg", ["<>1024", "<NaN"])
def test_numeric_filter_raises(mk_filestats, invalid_arg):
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
def test_path_filter(mk_filestats, reg_pat, paths, results):
    path_filter = mk_filestats.RegexFilter(reg_pat)
    for path, result in zip(paths, results):
        lazy_file = mk_filestats.FileStat(path)
        assert result == path_filter.matches(lazy_file)


@pytest.mark.parametrize(
    "config",
    [
        {
            "filter_foo": None
        },
        {
            "filter_size": "!=käse"
        },
    ],
)
def test_get_file_filters_invalid(mk_filestats, config):
    with pytest.raises(ValueError):
        mk_filestats.get_file_filters(config)


def test_get_file_filters(mk_filestats):
    config = {"filter_size": ">1", "filter_age": "==0", "filter_regex": "foo"}
    filters = mk_filestats.get_file_filters(config)
    assert len(filters) == 3
    assert isinstance(filters[0], mk_filestats.RegexFilter)
    assert isinstance(filters[1], mk_filestats.AbstractNumericFilter)
    assert isinstance(filters[2], mk_filestats.AbstractNumericFilter)


@pytest.mark.parametrize("config", [{}, {"output": "/dev/null"}])
def test_get_ouput_aggregator_invalid(mk_filestats, config):
    with pytest.raises(ValueError):
        mk_filestats.get_output_aggregator(config)


@pytest.mark.parametrize("output_value", ["count_only", "file_stats", "single_file"])
def test_get_ouput_aggregator(mk_filestats, output_value):
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
def test_output_aggregator_single_file_servicename(mk_filestats, lazyfile, group_name, expected):

    actual = mk_filestats.output_aggregator_single_file(group_name, [lazyfile])
    assert expected == list(actual)[0]


@pytest.mark.parametrize("val", [None, "null"])
def test_explicit_null_in_filestat(val, mk_filestats):
    FilestatFake = namedtuple("FilestatFake", ["size", "age", "stat_status"])
    filestat = FilestatFake(val, val, "file vanished")

    assert not mk_filestats.SizeFilter(">=1024").matches(filestat)
    assert not mk_filestats.AgeFilter(">=1024").matches(filestat)
