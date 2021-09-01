#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.events import add_to_event_context, EventContext, raw_context_from_string


@pytest.mark.parametrize("context,expected", [
    ("", {}),
    ("TEST=test", {
        "TEST": "test"
    }),
    ("SERVICEOUTPUT=with_light_vertical_bar_\u2758", {
        "SERVICEOUTPUT": "with_light_vertical_bar_|"
    }),
    ("LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758", {
        "LONGSERVICEOUTPUT": "with_light_vertical_bar_|"
    }),
    ("NOT_INFOTEXT=with_light_vertical_bar_\u2758", {
        "NOT_INFOTEXT": "with_light_vertical_bar_\u2758"
    }),
])
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


@pytest.mark.parametrize("param, expected", [
    pytest.param(
        {'param': 'value'},
        {'PARAMETER_PARAM': 'value'},
        id="add_str_to_context",
    ),
    pytest.param(
        {'param': 42},
        {'PARAMETER_PARAM': '42'},
        id="add_int_to_context",
    ),
    pytest.param(
        {'param': 42.5},
        {'PARAMETER_PARAM': '42.5'},
        id="add_float_to_context",
    ),
    pytest.param(
        {'param': True},
        {'PARAMETER_PARAM': 'True'},
        id="add_bool_to_context",
    ),
    pytest.param(
        {'dict': {
            'key': 'value'
        }},
        {'PARAMETER_DICT_KEY': 'value'},
        id="add_from_simple_dict",
    ),
    pytest.param(
        ("foo", "bar", "baz"),
        {'PARAMETER': 'foo\tbar\tbaz'},
        id="add_from_simple_tuple",
    ),
    pytest.param(
        {
            'smtp': {
                'smarthosts': ['127.0.0.1', '127.0.0.2', '127.0.0.3'],
                'port': 25,
                'auth': {
                    'method': 'plaintext',
                    'user': 'user',
                    'password': 'password'
                },
                'encryption': 'starttls'
            }
        },
        {
            'PARAMETER_SMTP_SMARTHOSTSS': '127.0.0.1 127.0.0.2 127.0.0.3',
            'PARAMETER_SMTP_SMARTHOSTS_1': '127.0.0.1',
            'PARAMETER_SMTP_SMARTHOSTS_2': '127.0.0.2',
            'PARAMETER_SMTP_SMARTHOSTS_3': '127.0.0.3',
            'PARAMETER_SMTP_PORT': '25',
            'PARAMETER_SMTP_AUTH_METHOD': 'plaintext',
            'PARAMETER_SMTP_AUTH_USER': 'user',
            'PARAMETER_SMTP_AUTH_PASSWORD': 'password',
            'PARAMETER_SMTP_ENCRYPTION': 'starttls'
        },
        id="add_from_dict",
    ),
    pytest.param(
        {'elements': ['omdsite', 'hosttags', 'address', 'abstime']},
        {
            'PARAMETER_ELEMENTSS': 'omdsite hosttags address abstime',
            'PARAMETER_ELEMENTS_1': 'omdsite',
            'PARAMETER_ELEMENTS_2': 'hosttags',
            'PARAMETER_ELEMENTS_3': 'address',
            'PARAMETER_ELEMENTS_4': 'abstime',
        },
        id="add_from_list",
    ),
    pytest.param(
        {
            'key': ("one", "two"),
            'key1': ("one", "two", "three"),
        },
        {
            'PARAMETER_KEY': 'one\ttwo',
            'PARAMETER_KEY1': 'one\ttwo\tthree',
        },
        id="add_from_tuple",
    ),
])
def test_add_to_event_context(param: object, expected: EventContext) -> None:
    context: EventContext = {}
    add_to_event_context(context, "PARAMETER", param)
    assert context == expected
