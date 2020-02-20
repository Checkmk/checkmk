# encoding: utf-8

import pytest  # type: ignore[import]

from cmk.base import events


@pytest.mark.parametrize("context,expected", [
    (b"", {}),
    (b"TEST=test", {
        "TEST": "test"
    }),
    (b"SERVICEOUTPUT=with_light_vertical_bar_\xe2\x9d\x98", {
        "SERVICEOUTPUT": "with_light_vertical_bar_|"
    }),
    (b"LONGSERVICEOUTPUT=with_light_vertical_bar_\xe2\x9d\x98", {
        "LONGSERVICEOUTPUT": "with_light_vertical_bar_|"
    }),
    (b"NOT_INFOTEXT=with_light_vertical_bar_\xe2\x9d\x98", {
        "NOT_INFOTEXT": "with_light_vertical_bar_\u2758"
    }),
])
def test_raw_context_from_string(context, expected):
    assert events.raw_context_from_string(context) == expected
