# encoding: utf-8

import io

import pytest

from cmk_base import events


def raw_context_test_cases():
    return [
        ("", {}),
        ("TEST=test", {
            "TEST": "test"
        }),
        ("SERVICEOUTPUT=with_light_vertical_bar_\xe2\x9d\x98", {
            "SERVICEOUTPUT": "with_light_vertical_bar_|"
        }),
        ("LONGSERVICEOUTPUT=with_light_vertical_bar_\xe2\x9d\x98", {
            "LONGSERVICEOUTPUT": "with_light_vertical_bar_|"
        }),
        ("NOT_INFOTEXT=with_light_vertical_bar_\xe2\x9d\x98", {
            "NOT_INFOTEXT": "with_light_vertical_bar_\xe2\x9d\x98"
        }),
    ]


@pytest.mark.parametrize("context,expected", raw_context_test_cases())
def test_raw_context_from_string(context, expected):
    assert events.raw_context_from_string(context) == expected


@pytest.mark.parametrize("context,expected", raw_context_test_cases())
def test_raw_context_from_stdin(monkeypatch, context, expected):
    monkeypatch.setattr('sys.stdin', io.BytesIO(context))
    assert events.raw_context_from_stdin() == expected
