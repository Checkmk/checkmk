# encoding: utf-8

import io
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
def test_raw_context_from_env_pipe_decoding(monkeypatch, environ, expected):
    monkeypatch.setattr(os, 'environ', environ)
    assert notify.raw_context_from_env() == expected


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
def test_raw_context_from_stdin(monkeypatch, context, expected):
    monkeypatch.setattr('sys.stdin', io.StringIO(context))
    assert notify.raw_context_from_stdin() == expected
