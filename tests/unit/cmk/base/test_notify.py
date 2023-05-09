#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest  # type: ignore[import]

from cmk.base import notify


def test_os_environment_does_not_override_notification_script_env(monkeypatch):
    """Regression test for Werk #7339"""
    monkeypatch.setattr(os, 'environ', {'NOTIFY_CONTACTEMAIL': ''})
    script_env = notify.notification_script_env({'CONTACTEMAIL': 'ab@test.de'})
    assert script_env == {'NOTIFY_CONTACTEMAIL': 'ab@test.de'}


@pytest.mark.parametrize("environ,expected", [
    ({}, {}),
    (
        {
            'TEST': 'test'
        },
        {},
    ),
    (
        {
            'NOTIFY_TEST': 'test'
        },
        {
            'TEST': 'test'
        },
    ),
    (
        {
            'NOTIFY_SERVICEOUTPUT': 'LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758'
        },
        {
            'SERVICEOUTPUT': 'LONGSERVICEOUTPUT=with_light_vertical_bar_|'
        },
    ),
    (
        {
            'NOTIFY_LONGSERVICEOUTPUT': 'LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758'
        },
        {
            'LONGSERVICEOUTPUT': 'LONGSERVICEOUTPUT=with_light_vertical_bar_|'
        },
    ),
])
def test_raw_context_from_env_pipe_decoding(environ, expected):
    assert notify.raw_context_from_env(environ) == expected
