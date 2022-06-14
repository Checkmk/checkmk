#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import math
from typing import Any, Dict

import pytest

from tests.testlib.base import Scenario

from cmk.utils.type_defs import CheckPluginName

import cmk.base.config as config
import cmk.base.plugin_contexts as plugin_contexts
from cmk.base import check_api


@pytest.mark.parametrize("value_eight", ["8", 8])
def test_oid_spec_binary(value_eight) -> None:
    oid_bin = check_api.BINARY(value_eight)
    assert oid_bin.column == "8"
    assert oid_bin.encoding == "binary"
    assert oid_bin.save_to_cache is False


@pytest.mark.parametrize("value_eight", ["8", 8])
def test_oid_spec_cached(value_eight) -> None:
    oid_cached = check_api.CACHED_OID(value_eight)
    assert oid_cached.column == "8"
    assert oid_cached.encoding == "string"
    assert oid_cached.save_to_cache is True


@check_api.get_parsed_item_data
def check_foo(item, params, parsed_item_data):
    return 2, "bar"


def test_get_parsed_item_data() -> None:
    params: Dict[Any, Any] = {}
    parsed = {1: "one", 3: {}, 4: [], 5: ""}
    info = [[1, "one"], [2, "two"]]
    assert check_foo(1, params, parsed) == (2, "bar")
    assert check_foo(2, params, parsed) is None
    assert check_foo(3, params, parsed) is None
    assert check_foo(4, params, parsed) is None
    assert check_foo(5, params, parsed) is None
    output = (3, "Wrong usage of decorator function 'get_parsed_item_data': parsed is not a dict")
    assert check_foo(1, params, info) == output
    assert check_foo.__name__ == "check_foo"


def test_validate_filter() -> None:
    assert check_api.validate_filter(sum)((1, 4)) == 5

    with pytest.raises(ValueError):
        check_api.validate_filter("nothing")

    assert check_api.validate_filter(None)(1, 4) == 1


@pytest.mark.parametrize(
    "parsed, result",
    [
        (None, None),
        ([], None),
        ({}, None),
        ([["enabled"]], [(None, {})]),
        ({"first": "enabled"}, [(None, {})]),
    ],
)
def test_discover_single(parsed, result) -> None:
    assert check_api.discover_single(parsed) == result


@pytest.mark.parametrize(
    "parsed, selector, result",
    [
        ({}, lambda x: x, None),
        (
            {
                "one": None,
                "two": None,
            },
            None,
            [("one", {}), ("two", {})],
        ),
        (
            {
                "one": None,
                "two": None,
            },
            lambda k, v: k,
            [("one", {}), ("two", {})],
        ),
        (
            {
                "one": None,
                "two": None,
            },
            lambda k, v: k.startswith("o"),
            [("one", {})],
        ),
        (
            {
                "one": None,
                "two": None,
            },
            lambda k, v: k == "one",
            [("one", {})],
        ),
        (
            {
                "one": "enabled",
                "two": {"load": 10, "max": 50},
                "three": ["load", "capacity"],
            },
            lambda k, values: "load" in values if isinstance(values, dict) else False,
            [("two", {})],
        ),
        (
            {
                "one": "enabled",
                "two": {"load": 10, "max": 50, "Innodb_data_read": True},
            },
            lambda k, values: "Innodb_data_read" in values,
            [("two", {})],
        ),
        (
            {
                "one": "enabled",
                "two": {"load": 10, "Innodb_data_read": True},
            },
            lambda key, values: all(val in values for val in ["load", "max"]),
            None,
        ),
        (
            {
                "one": [1],
                "two": [2],
                "three": [3],
                "four": (),
                "five": [],
            },
            lambda k, value: len(value) > 0,
            [
                ("one", {}),
                ("two", {}),
                ("three", {}),
            ],
        ),
        (
            [["one", 5, 3], ["two", 0, 0], ["three", 2, 8]],
            lambda line: line[0],
            [
                ("one", {}),
                ("two", {}),
                ("three", {}),
            ],
        ),
        (
            [["one", 5, 3], ["two", 0, 0], ["three", 2, 8]],
            lambda line: line[0].upper() if line[1] > 0 else False,
            [
                ("ONE", {}),
                ("THREE", {}),
            ],
        ),
    ],
)
def test_discover_inputs_and_filters(parsed, selector, result) -> None:
    items = list(check_api.discover(selector)(parsed))
    for item in items:
        assert item in result

    if result is not None:
        assert len(items) == len(result)
    else:
        assert items == []


def test_discover_decorator_key_match() -> None:
    @check_api.discover
    def selector(key, value):
        return key == "hello"

    # Pylint does not understand our decorator magic here. Investigate
    assert list(
        selector({"hola": "es", "hello": "en"})  # pylint:disable=no-value-for-parameter
    ) == [("hello", {})]


def test_discover_decorator_with_params() -> None:
    @check_api.discover(default_params="empty")
    def selector2(entry):
        return "hello" in entry

    assert list(selector2([["hello", "world"], ["hola", "mundo"]])) == [("hello", "empty")]


def test_discover_decorator_returned_name() -> None:
    @check_api.discover
    def inventory_thecheck(key, value):
        required_entries = ["used", "ready"]
        if all(data in value for data in required_entries):
            return key.upper()
        return None

    data = {
        "host": [["mysql", 10, 10], ["home", 5, 8]],
        "house": [["performance_schema", 5, 7], ["test", 1, 5]],
        "try": ["used", "ready", "total"],
    }

    # Pylint does not understand our decorator magic here. Investigate
    assert list(inventory_thecheck(data)) == [("TRY", {})]  # pylint: disable=no-value-for-parameter


def test_discover_decorator_with_nested_entries() -> None:
    @check_api.discover
    def nested_discovery(instance, values):
        for dbname, used, avail in values:
            if (
                dbname not in ["information_schema", "mysql", "performance_schema"]
                and used != "NULL"
                and avail != "NULL"
            ):
                yield "%s:%s" % (instance, dbname)

    data = {
        "host": [["mysql", 10, 10], ["home", 5, 8]],
        "house": [["performance_schema", 5, 7], ["test", 1, 5]],
    }

    # Pylint does not understand our decorator magic here. Investigate
    assert sorted(nested_discovery(data)) == [  # pylint: disable=no-value-for-parameter
        ("host:home", {}),
        ("house:test", {}),
    ]


@pytest.mark.parametrize(
    "parsed, selector, error",
    [
        (
            {
                "one": None,
                "two": None,
            },
            lambda k: k,
            (TypeError, r"takes 1 positional argument but 2 were"),
        ),
        (None, lambda k, v: k.startswith("o"), (ValueError, "and tuples you gave a")),
        (list(range(5)), lambda k, v: v == k, (TypeError, r"missing 1 required positional")),
    ],
)
def test_discover_exceptions(parsed, selector, error) -> None:
    with pytest.raises(error[0], match=error[1]):
        next(check_api.discover(selector)(parsed))


@pytest.mark.parametrize(
    "value, levels, representation, unit, result",
    [
        (5, (3, 6), int, "", (1, " (warn/crit at 3/6)")),
        (7, (3, 6), lambda x: "%.1f m" % x, "", (2, " (warn/crit at 3.0 m/6.0 m)")),
        (7, (3, 6), lambda x: "%.1f" % x, " m", (2, " (warn/crit at 3.0 m/6.0 m)")),
        (2, (3, 6, 1, 0), int, "", (0, "")),
        (1, (3, 6, 1, 0), int, "", (0, "")),
        (0, (3, 6, 1, 0), int, "", (1, " (warn/crit below 1/0)")),
        (-1, (3, 6, 1, 0), int, "", (2, " (warn/crit below 1/0)")),
    ],
)
def test_boundaries(value, levels, representation, unit, result) -> None:
    assert check_api._do_check_levels(value, levels, representation, unit) == result


@pytest.mark.parametrize(
    "value, dsname, params, kwargs, result",
    [
        (
            5,
            "battery",
            None,
            {"human_readable_func": check_api.get_percent_human_readable},
            (0, "5.0%", [("battery", 5, None, None)]),
        ),
        (
            6,
            "disk",
            (4, 8),
            {"unit": "years", "infoname": "Disk Age"},
            (1, "Disk Age: 6.00 years (warn/crit at 4.00 years/8.00 years)", [("disk", 6.0, 4, 8)]),
        ),
        (
            5e-7,
            "H_concentration",
            (4e-7, 8e-7, 5e-8, 2e-8),
            {
                "human_readable_func": lambda x: "pH %.1f" % -math.log10(x),
                "infoname": "Water acidity",
            },
            (
                1,
                "Water acidity: pH 6.3 (warn/crit at pH 6.4/pH 6.1)",
                [("H_concentration", 5e-7, 4e-7, 8e-7)],
            ),
        ),
        (
            5e-7,
            "H_concentration",
            (4e-7, 8e-7, 5e-8, 2e-8),
            {
                "human_readable_func": lambda x: "pH %.1f" % -math.log10(x),
                "unit": "??",
                "infoname": "Water acidity",
            },
            (
                1,
                "Water acidity: pH 6.3 ?? (warn/crit at pH 6.4 ??/pH 6.1 ??)",
                [("H_concentration", 5e-7, 4e-7, 8e-7)],
            ),
        ),
    ],
)
def test_check_levels(value, dsname, params, kwargs, result) -> None:
    assert check_api.check_levels(value, dsname, params, **kwargs) == result


def test_http_proxy(mocker) -> None:
    proxy_patch = mocker.patch.object(config, "get_http_proxy")
    check_api.get_http_proxy(("url", "http://xy:123"))
    assert proxy_patch.called_once()


def test_get_effective_service_level(monkeypatch) -> None:
    ts = Scenario()
    ts.add_host("testhost1")
    ts.add_host("testhost2")
    ts.add_host("testhost3")
    ts.set_ruleset(
        "host_service_levels",
        [
            (10, [], ["testhost2"], {}),
            (2, [], ["testhost2"], {}),
        ],
    )
    ts.set_ruleset(
        "service_service_levels",
        [
            (33, [], ["testhost1"], ["CPU load$"], {}),
        ],
    )
    ts.apply(monkeypatch)

    with plugin_contexts.current_service(CheckPluginName("cpu_loads"), "CPU load"):

        with plugin_contexts.current_host("testhost1"):
            assert check_api.get_effective_service_level() == 33

        with plugin_contexts.current_host("testhost2"):
            assert check_api.get_effective_service_level() == 10

        with plugin_contexts.current_host("testhost3"):
            assert check_api.get_effective_service_level() == 0


def test_as_float() -> None:
    assert check_api.as_float("8.00") == 8.0
    assert str(check_api.as_float("inf")) == "inf"

    strrep = str(list(map(check_api.as_float, ("8", "-inf", "1e-351"))))
    assert strrep == "[8.0, -1e309, 0.0]"

    assert ast.literal_eval(strrep) == [8.0, float("-inf"), 0.0]
