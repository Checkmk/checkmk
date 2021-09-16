#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.events import add_to_event_context, EventContext, raw_context_from_string


@pytest.mark.parametrize(
    "context,expected",
    [
        ("", {}),
        ("TEST=test", {"TEST": "test"}),
        (
            "SERVICEOUTPUT=with_light_vertical_bar_\u2758",
            {"SERVICEOUTPUT": "with_light_vertical_bar_|"},
        ),
        (
            "LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758",
            {"LONGSERVICEOUTPUT": "with_light_vertical_bar_|"},
        ),
        (
            "NOT_INFOTEXT=with_light_vertical_bar_\u2758",
            {"NOT_INFOTEXT": "with_light_vertical_bar_\u2758"},
        ),
    ],
)
def test_raw_context_from_string(context: str, expected: EventContext) -> None:
    assert raw_context_from_string(context) == expected


def test_add_to_event_context_param_overrides_context() -> None:
    context: EventContext = {"FOO": "bar", "BAZ": "old"}
    add_to_event_context(context, "BAZ", "new")
    assert context == {"FOO": "bar", "BAZ": "new"}


def test_add_to_event_context_prefix_is_prepended() -> None:
    context: EventContext = {}
    add_to_event_context(context, "FOO", "bar")
    add_to_event_context(context, "BAZ", "boo")
    add_to_event_context(context, "AAA", {"BBB": "CCC"})
    assert context == {"FOO": "bar", "BAZ": "boo", "AAA_BBB": "CCC"}


@pytest.mark.parametrize(
    "param, expected",
    [
        # basic types ----------------------------------------------------------
        pytest.param(
            "blah",
            {"PARAMETER": "blah"},
            id="string",
        ),
        pytest.param(
            12345,
            {"PARAMETER": "12345"},
            id="int",
        ),
        pytest.param(
            1234.5,
            {"PARAMETER": "1234.5"},
            id="float",
        ),
        pytest.param(
            None,
            {"PARAMETER": ""},
            id="None",
        ),
        pytest.param(
            True,
            {"PARAMETER": "True"},
            id="True",
        ),
        pytest.param(
            False,
            {"PARAMETER": "False"},
            id="False",
        ),
        # lists ----------------------------------------------------------------
        pytest.param(
            [],
            {"PARAMETERS": ""},
            id="empty list",
        ),
        pytest.param(
            ["blah"],
            {
                "PARAMETERS": "blah",
                "PARAMETER_1": "blah",
            },
            id="singleton list with string",
        ),
        pytest.param(
            ["foo", "bar", "baz"],
            {
                "PARAMETERS": "foo bar baz",
                "PARAMETER_1": "foo",
                "PARAMETER_2": "bar",
                "PARAMETER_3": "baz",
            },
            id="general list with strings",
        ),
        pytest.param(
            [42, {"caller": "admin", "urgency": "low"}],
            {
                "PARAMETER_1": "42",
                "PARAMETER_2_CALLER": "admin",
                "PARAMETER_2_URGENCY": "low",
            },
            id="list with non-string elements",
        ),
        # tuples ---------------------------------------------------------------
        pytest.param(
            (),
            {"PARAMETER": ""},
            id="empty tuple",
        ),
        pytest.param(
            ("blah",),
            {
                "PARAMETER": "blah",
                "PARAMETER_1": "blah",
            },
            id="singleton tuple with string",
        ),
        pytest.param(
            ("foo", "bar", "baz"),
            {
                "PARAMETER": "foo\tbar\tbaz",
                "PARAMETER_1": "foo",
                "PARAMETER_2": "bar",
                "PARAMETER_3": "baz",
            },
            id="general tuple with strings",
        ),
        pytest.param(
            (42, {"caller": "admin", "urgency": "low"}),
            {
                "PARAMETER_1": "42",
                "PARAMETER_2_CALLER": "admin",
                "PARAMETER_2_URGENCY": "low",
            },
            id="tuple with non-string elements",
        ),
        # dicts ----------------------------------------------------------------
        pytest.param(
            {},
            {},
            id="empty dict",
        ),
        pytest.param(
            {"key": "value"},
            {"PARAMETER_KEY": "value"},
            id="dict with a single string/string entry",
        ),
        pytest.param(
            {
                "key": 42,
                "foo": True,
                "ernie": "Bert",
                "bar": {
                    "baz": {
                        "blubb": 2.5,
                        "smarthosts": ["127.0.0.1", "127.0.0.2", "127.0.0.3"],
                        "nephews": ("Huey", "Dewey", "Louie"),
                    },
                    "ding": "dong",
                },
            },
            {
                "PARAMETER_KEY": "42",
                "PARAMETER_FOO": "True",
                "PARAMETER_ERNIE": "Bert",
                "PARAMETER_BAR_BAZ_BLUBB": "2.5",
                "PARAMETER_BAR_BAZ_SMARTHOSTSS": "127.0.0.1 127.0.0.2 127.0.0.3",
                "PARAMETER_BAR_BAZ_SMARTHOSTS_1": "127.0.0.1",
                "PARAMETER_BAR_BAZ_SMARTHOSTS_2": "127.0.0.2",
                "PARAMETER_BAR_BAZ_SMARTHOSTS_3": "127.0.0.3",
                "PARAMETER_BAR_BAZ_NEPHEWS": "Huey\tDewey\tLouie",
                "PARAMETER_BAR_BAZ_NEPHEWS_1": "Huey",
                "PARAMETER_BAR_BAZ_NEPHEWS_2": "Dewey",
                "PARAMETER_BAR_BAZ_NEPHEWS_3": "Louie",
                "PARAMETER_BAR_DING": "dong",
            },
            id="dict with multiple string/mixed entries",
        ),
    ],
)
def test_add_to_event_context(param: object, expected: EventContext) -> None:
    context: EventContext = {}
    add_to_event_context(context, "PARAMETER", param)
    assert context == expected
