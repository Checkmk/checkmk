#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base import events


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
def test_raw_context_from_string(context, expected):
    assert events.raw_context_from_string(context) == expected


@pytest.mark.parametrize("context, prefix, param, expected", [
    pytest.param(
        {},
        "PARAMETER",
        {
            'param': 'value',
        },
        {
            'PARAMETER_PARAM': 'value',
        },
        id="add_str_to_context",
    ),
    pytest.param(
        {},
        "PARAMETER",
        {
            'param': 42,
        },
        {
            'PARAMETER_PARAM': '42',
        },
        id="add_int_to_context",
    ),
    pytest.param(
        {},
        "PARAMETER",
        {
            'param': 42.0,
        },
        {
            'PARAMETER_PARAM': '42.0',
        },
        id="add_float_to_context",
    ),
    pytest.param(
        {},
        "PARAMETER",
        {
            'param': True,
        },
        {
            'PARAMETER_PARAM': 'True',
        },
        id="add_bool_to_context",
    ),
    pytest.param(
        {},
        "PARAMETER",
        {'dict': {
            'key': 'value'
        }},
        {
            'PARAMETER_DICT_KEY': 'value',
        },
        id="add_from_simple_dict",
    ),
    pytest.param(
        {},
        "PARAMETER",
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
        {},
        "PARAMETER",
        {'elements': [
            'omdsite',
            'hosttags',
            'address',
            'abstime',
        ]},
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
        {},
        "PARAMETER",
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
def test_add_to_event_context(context, prefix, param, expected):
    events.add_to_event_context(context, prefix, param)
    assert context == expected
